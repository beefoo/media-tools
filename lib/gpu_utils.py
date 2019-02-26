# -*- coding: utf-8 -*-

import numpy as np
import os
from pprint import pprint
import pyopencl as cl
import sys

from lib.clip import *

os.environ['PYOPENCL_COMPILER_OUTPUT'] = '1'

def clipsToDictsGPU(clips, ms, container=None, precision=5):
    clipCount = len(clips)
    clipPropertyInCount = len(Clip.CLIP_PROPERTIES.keys())
    clipPropertyOutCount = 8
    keyframePropertyCount = len(Clip.KEYFRAME_PROPERTIES.keys())
    precisionMultiplier = int(10 ** precision)

    # init container data
    containerKeyframeCount = len(container.vector.keyframes)
    containerPlayCount = 0
    containerDataIn = container.toGPUArray(ms, containerPlayCount, containerKeyframeCount, precision) if container is not None else np.array([-1], dtype=np.int32)

    # init clip data; determine keyframe count
    playCount = max([len(clip.plays) for clip in clips])
    kfCount = max([len(clip.vector.keyframes) for clip in clips])
    clipsDataIn = np.zeros((clipCount, clipPropertyInCount + kfCount*keyframePropertyCount + playCount*2)), dtype=np.int32)
    for clip in clips:
        clipsDataIn[clip.props["index"]] = clip.toGPUArray(ms, playCount, kfCount, precision)

    clipsDataIn = clipsDataIn.reshape(-1)
    result = np.zeros(clipCount * clipPropertyOutCount, dtype=np.int32)

    # transform constants to string
    propertyString = " ".join(["int %s = %d;" % (key, value) for key, value in Clip.CLIP_PROPERTIES.items()])
    keyframeString = " ".join(["int %s = %d;" % (key, value) for key, value in Clip.KEYFRAME_PROPERTIES.items()])
    keyframePropsString = " ".join(["int props_%s = %d;" % (key, value) for key, value in Clip.PROPERTY_NAMES.items()])
    easingPropsString = " ".join(["int easing_%s = %d;" % (key, value) for key, value in Clip.EASING_PROPERTIES.items()])

    srcCode = """
    static bool isClipVisible(int x, int y, int w, int h, int alpha, int containerW, int containerH) {
        return (containerW<=0 || containerH <= 0 || ((x+w) > 0 && (y+h) > 0 && (x<containerW) && (y<containerH) && alpha > 0));
    }

    static int lerp(int fromValue, int toValue, float amount) {
        return (int)round((float)(toValue-fromValue) * amount) + fromValue;
    }

    static int lerpEase(int fromValue, int toValue, float amount, int easing) {
        float pi = 3.1415926535897932384;
        %s // easing names
        if (easing == easing_sin) {
            amount = (sin((amount+1.5)*pi)+1.0) / 2.0;
        } else if (easing == easing_cubicInOut) {
            if (amount < 0.5) { amount = 4.0 * pow(amount, 3.0); }
            else { amount = (amount-1.0)*(2.0*amount-2.0)*(2.0*amount-2.0)+1.0; }
        } else if (easing == easing_quartInOut) {
            if (amount < 0.5) { amount = 8.0 * pow(amount, 4.0); }
            else { amount = 1.0 - 8.0 * pow((amount-1.0), 4.0); }
        }
        return lerp(fromValue, toValue, amount);
    }

    static float norm(int value, int a, int b) {
        return (float)(value - a) / (float)(b - a);
    }

    int getClipTime(__global int *clipsData, int ms, int offsetIn, float precisionMultiplierF, int playCount, int dur);
    int10 getKeyframedProperties(__global int *clipsData, int ms, int offsetIn, float precisionMultiplierF, int clipPropertyInCount, int keyframePropertyCount, int kfCount, int containerX, int containerY, int containerW, int containerH, int containerFromW, int containerFromH);

    int getClipTime(__global int *clipsData, int ms, int offsetIn, float precisionMultiplierF, int playCount, int dur) {
        int closestFromMs = 0;
        int closestMs = -1;

        // find the closest play
        for (int i=0; i<playCount; i++) {
            int poffset = offsetIn + i * 2;
            int fromMs = clipsData[poffset];
            int toMs = clipsData[poffset+1];
            if ((fromMs > 0 || toMs > 0)) {
                int distanceMs = abs(ms - lerp(fromMs, toMs, 0.5));
                if (closestMs < 0 || distanceMs < closestMs) {
                    closestMs = distanceMs;
                    closestFromMs = fromMs;
                }
            }
        }

        int msSincePlay = ms - closestFromMs;
        int remainder = msSincePlay % dur;
        int time = (int) round((float) remainder / (float) dur * precisionMultiplierF);

        return time;
    }

    int10 getKeyframedProperties(__global int *clipsData, int ms, int offsetIn, float precisionMultiplierF, int clipPropertyInCount, int keyframePropertyCount, int kfCount, int containerX, int containerY, int containerW, int containerH, int containerFromW, int containerFromH) {
        %s // keyframe properties
        %s // property names for keyframes

        // get clip properties
        int2 pos = (int2)(clipsData[offsetIn + X], clipsData[offsetIn + Y]);
        int2 size = (int2)(clipsData[offsetIn + WIDTH], clipsData[offsetIn + HEIGHT]);
        int fromW = size.x;
        int fromH = size.y;
        int alpha = clipsData[offsetIn + ALPHA];
        int zindex = clipsData[offsetIn + Z];
        float2 origin = (float2)((float)clipsData[offsetIn + ORIGIN_X]/precisionMultiplierF, (float)clipsData[offsetIn + ORIGIN_Y]/precisionMultiplierF);
        float2 transformOrigin = (float2)((float)clipsData[offsetIn + T_ORIGIN_X]/precisionMultiplierF, (float)clipsData[offsetIn + T_ORIGIN_Y]/precisionMultiplierF);
        int dur = clipsData[offsetIn + DUR];
        int index = clipsData[offsetIn + INDEX];

         // pos
        int xFrom = 0; int xTo = 0; int yFrom = 0; int yTo = 0; int posEasing = 1;
        int xFromMs = -1; int yFromMs = -1; float xAmount = 0.0; float yAmount = 0.0;
        bool xFromDone = false; bool yFromDone = false; bool xToDone = false; bool yToDone = false;
        // translate
        int txFrom = 0; int txTo = 0; int tyFrom = 0; int tyTo = 0; int translateEasing = 1;
        int txFromMs = -1; int tyFromMs = -1; float txAmount = 0.0; float tyAmount = 0.0;
        bool txFromDone = false; bool tyFromDone = false; bool txToDone = false; bool tyToDone = false;
        // scale
        int sxFrom = 0; int sxTo = 0; int syFrom = 0; int syTo = 0; int scaleEasing = 1;
        int sxFromMs = -1; int syFromMs = -1; float sxAmount = 0.0; float syAmount = 0.0;
        bool sxFromDone = false; bool syFromDone = false; bool sxToDone = false; bool syToDone = false;
        // alpha
        int alphaFrom = 0; alphaTo = 0; int alphaEasing = 1;
        int alphaFromMs = -1; float alphaAmount = 0.0;
        bool alphaFromDone = false; bool alphaToDone = false;

        // go through keyframes (assuming they are sorted)
        int keyframeOffset = offsetIn + clipPropertyInCount;
        for (int j=0; j<kfCount; j++) {
            int koffset = keyframeOffset + j * keyframePropertyCount;
            int kfMs = clipsData[koffset+KF_MS];
            int kfProp = clipsData[koffset+KF_PROPERTY];
            int kfDim = clipsData[koffset+KF_DIMENSION];
            int kfVal = clipsData[koffset+KF_VALUE];
            int kfEase = clipsData[koffset+KF_EASING];

            if (kfProp > 0) {
                // the keyframe is after the current ms; attempt to make it the "to" keyframe
                if (kfMs > ms) {
                    if (kfProp == props_pos) {
                        if (kfDim == 0 && !xToDone) {
                            xTo = kfVal; xToDone = true; posEasing = kfEase;
                            if (xFromMs >= 0) { xAmount = norm(ms, xFromMs, kfMs); }
                        } else if (kfDim == 1 && !yToDone) {
                            yTo = kfVal; yToDone = true; posEasing = kfEase;
                            if (yFromMs >= 0) { yAmount = norm(ms, yFromMs, kfMs); }
                        }
                    } else if (kfProp == props_translate) {
                        if (kfDim == 0 && !txToDone) {
                            txTo = kfVal; txToDone = true; translateEasing = kfEase;
                            if (txFromMs >= 0) { txAmount = norm(ms, txFromMs, kfMs); }
                        } else if (kfDim == 1 && !tyToDone) {
                            tyTo = kfVal; tyToDone = true; translateEasing = kfEase;
                            if (tyFromMs >= 0) { tyAmount = norm(ms, tyFromMs, kfMs); }
                        }
                    } else if (kProp == props_scale) {
                        if (kfDim == 0 && !sxToDone) {
                            sxTo = kfVal; sxToDone = true; scaleEasing = kfEase;
                            if (sxFromMs >= 0) { sxAmount = norm(ms, sxFromMs, kfMs); }
                        } else if (kfDim == 1 && !syToDone) {
                            syTo = kfVal; syToDone = true; scaleEasing = kfEase;
                            if (syFromMs >= 0) { syAmount = norm(ms, syFromMs, kfMs); }
                        } else if (!sxToDone && !syToDone) {
                            sxTo = kfVal; syTo = kfVal; sxToDone = true; syToDone = true; scaleEasing = kfEase;
                            if (sxFromMs >= 0) { sxAmount = norm(ms, sxFromMs, kfMs); }
                            if (syFromMs >= 0) { syAmount = norm(ms, syFromMs, kfMs); }
                        }
                    } else if (kProp == props_alpha) {
                        if (!alphaToDone) {
                            alphaTo = kfVal; alphaToDone = true; alphaEasing = kfEase;
                            if (alphaFromMs >= 0) { alphaAmount = norm(ms, alphaFromMs, kfMs); }
                        }
                    }
                // else the keyframe is before the current ms; make it the "from" keyframe
                } else {
                    if (kfProp == props_pos) {
                        if (kfDim == 0) { xFrom = kfVal; xFromDone = true; xFromMs = kfMs; }
                        else if (kfDim == 1) { yFrom= kfVal; yFromDone = true; yFromMs = kfMs; }
                    } else if (kfProp == props_translate) {
                        if (kfDim == 0) { txFrom = kfVal; txFromDone = true; txFromMs = kfMs; }
                        else if (kfDim == 1) { tyFrom = kfVal; tyFromDone = true; tyFromMs = kfMs; }
                    } else if (kProp == props_scale) {
                        if (kfDim == 0) { sxFrom= kfVal; sxFromDone = true; sxFromMs = kfMs; }
                        else if (kfDim == 1) { syFrom = kfVal; syFromDone = true; syFromMs = kfMs; }
                        else { sxFrom = kfVal; syFrom = kfVal; sxFromDone = true; syFromDone = true; sxFromMs = kfMs; syFromMs = kfMs; }
                    } else if (kProp == props_alpha) {
                        alphaFrom = kfVal; alphaFromDone = true; alphaFromMs = kfMs;
                    }
                }
            } // end if
        } // end for

        // determine x
        if (xFromDone && xToDone) { pos.x = lerpEase(xFrom, xTo, xAmount, posEasing); }
        else if (xFromDone) { pos.x = xFrom; }
        else if (xToDone) { pos.x = xTo; }

        // determine y
        if (yFromDone && yToDone) { pos.y = lerpEase(yFrom, yTo, yAmount, posEasing); }
        else if (yFromDone) { pos.y = yFrom; }
        else if (yToDone) { pos.y = yTo; }

        // account for origin
        pos.x = pos.x - (int)round((float)size.x * origin.x);
        pos.y = pos.y - (int)round((float)size.y * origin.y);

        // determine scale
        int scaleX = precisionMultiplier;
        if (sxFromDone && sxToDone) { scaleX = lerpEase(sxFrom, sxTo, sxAmount, scaleEasing); }
        else if (sxFromDone) { scaleX = sxFrom; }
        else if (sxToDone) { scaleX = sxTo; }
        float scaleXF = (float) scaleX / precisionMultiplierF;

        int scaleY = precisionMultiplier;
        if (syFromDone && syToDone) { scaleY = lerpEase(syFrom, syTo, syAmount, scaleEasing); }
        else if (syFromDone) { scaleY = syFrom; }
        else if (syToDone) { scaleY = syTo; }
        float scaleYF = (float) scaleY / precisionMultiplierF;

        // scale width/height
        size.x = (int) round((float) size.x * scaleXF);
        size.y = (int) round((float) size.y * scaleYF);

        // adjust position to account for scale
        pos.x = pos.x - (int) round((float)(size.x - fromW) * transformOrigin.x);
        pos.y = pos.y - (int) round((float)(size.y - fromH) * transformOrigin.y);

        // account for translate
        int translateX = 0;
        if (txFromDone && txToDone) { translateX = lerpEase(txFrom, txTo, txAmount, translateEasing); }
        else if (txFromDone) { translateX = txFrom; }
        else if (txToDone) { translateX = txTo; }
        int translateY = 0;
        if (tyFromDone && tyToDone) { translateY = lerpEase(tyFrom, tyTo, tyAmount, translateEasing); }
        else if (tyFromDone) { translateY = tyFrom; }
        else if (tyToDone) { translateY = tyTo; }
        pos.x += translateX;
        pos.y += translateY;

        // alpha
        if (alphaFromDone && alphaToDone) { alpha = lerpEase(alphaFrom, alphaTo, alphaAmount, alphaEasing); }
        else if (alphaFromDone) { alpha = alphaFrom; }
        else if (alphaToDone) { alpha = alphaTo; }

        // account for parent
        if (containerW > 0 && containerH > 0) {
            float nx = (float) pos.x / (float) containerFromW;
            pos.x = (int) round((float) containerW * nx) + containerX;
            float ny = (float) pos.y / (float) containerFromH;
            pos.y = (int) round((float) containerH * ny) + containerY;
        }

        return (int10)(pos.x, pos.y, size.x, size.y, alpha, zindex, dur, fromW, fromH, index);
    }

    __kernel void processClips(__global int *containerData, __global int *clipsData, __global int *result){
        %s // defines properties indices
        int i = get_global_id(0);
        int ms = %d;
        int clipPropertyInCount = %d;
        int clipPropertyOutCount = %d;
        int keyframePropertyCount = %d;
        int playCount = %d;
        int kfCount = %d;
        int containerKeyframeCount = %d;
        int precisionMultiplier = %d;
        float precisionMultiplierF = (float)precisionMultiplier;

        // get container properties
        int containerX = 0; int containerY = 0;
        int containerFromW = 0; int containerFromH = 0;
        int containerW = 0; int containerH = 0;

        if (containerData[0] >= 0) {
            int10 containerProps = getKeyframedProperties(containerData, ms, 0, precisionMultiplierF, clipPropertyInCount, keyframePropertyCount, containerKeyframeCount, 0, 0, 0, 0, 0, 0);
            containerX = containerProps[0]; containerY = containerProps[1];
            containerW = containerProps[2]; containerH = containerProps[3];
            containerFromW = containerProps[7]; containerFromH = containerProps[8];
        }

        // get keyframed clip properties
        int offsetIn = i * (clipPropertyInCount + keyframePropertyCount * kfCount + playCount * 2);
        int10 clipProps = getKeyframedProperties(clipsData, ms, offsetIn, precisionMultiplierF, clipPropertyInCount, keyframePropertyCount, kfCount, containerX, containerY, containerW, containerH, containerFromW, containerFromH);

        // get the time based on plays
        offsetIn += clipPropertyInCount + keyframePropertyCount * kfCount;
        int dur = clipProps[6];
        int time = getClipTime(clipsData, ms, offsetIn, precisionMultiplierF, playCount, dur);

        int x = clipProps[0];
        int y = clipProps[1];
        int w = clipProps[2];
        int h = clipProps[3];
        int alpha = clipProps[4];

        bool isVisible = isClipVisible(x, y, w, h, containerFromW, containerFromH);
        int offset = i * clipPropertyOutCount;
        if (isVisible) {
            result[offset] = x;
            result[offset+1] = y;
            result[offset+2] = w;
            result[offset+3] = h;
            result[offset+4] = alpha;
            result[offset+5] = time;
            result[offset+6] = clipProps[5]; // zindex
        }
        result[offset+7] = clipProps[9]; // index
    }
    """ % (easingPropsString, keyframeString, keyframePropsString, propertyString, ms, clipPropertyInCount, clipPropertyOutCount, keyframePropertyCount, playCount, kfCount, containerKeyframeCount, precisionMultiplier)

    ctx, mf, queue, prg = loadGPUProgram(srcCode)

    bufIn1 =  cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=containerDataIn)
    bufIn2 =  cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=clipsDataIn)
    bufOut = cl.Buffer(ctx, mf.WRITE_ONLY, hostbuf=result.nbytes)
    prg.processClips(queue, (clipCount, ), None , bufIn1, bufIn2, bufOut)

    # Copy result
    cl.enqueue_copy(queue, result, bufOut)
    result = result.reshape((clipCount, clipPropertyOutCount))
    return result

def clipsToImageGPU(width, height, flatPixelData, properties, colorDimensions, precision):
    count = len(properties)
    precisionMultiplier = int(10 ** precision)
    pcount = len(properties[0])
    properties = properties.reshape(-1)
    zvalues = np.zeros(width * height, dtype=np.int32)
    result = np.zeros(width * height * 3, dtype=np.uint8)

    # the kernel function
    srcCode = """
    static float norm(float value, float a, float b) {
        float n = (value - a) / (b - a);
        return n;
    }

    static int4 blendColors(int4 color1, int4 color2, float amount) {
        float invAmount = 1.0 - amount;

        // x, y, z, w = r, g, b, a
        int r = (int) round(((float) color1.x * amount) + ((float) color2.x * invAmount));
        int g = (int) round(((float) color1.y * amount) + ((float) color2.y * invAmount));
        int b = (int) round(((float) color1.z * amount) + ((float) color2.z * invAmount));
        int a = (int) round(((float) color1.w * amount) + ((float) color2.w * invAmount));

        return (int4)(r, g, b, a);
    }

    int4 getPixel(__global uchar *pdata, int x, int y, int h, int w, int dim, int offset);
    int4 getPixelF(__global uchar *pdata, float xF, float yF, int h, int w, int dim, int offset);

    int4 getPixel(__global uchar *pdata, int x, int y, int h, int w, int dim, int offset) {
        // check bounds; retain rgb color of edge, but make alpha=0
        bool isVisible = true;
        if (x < 0) { isVisible = false; x = 0; }
        if (y < 0) { isVisible = false; y = 0; }
        if (x >= w) { isVisible = false; x = w-1; }
        if (y >= h) { isVisible = false; y = h-1; }

        int index = y * w * dim + x * dim + offset;
        int r = pdata[index];
        int g = pdata[index+1];
        int b = pdata[index+2];
        int a = 255;
        if (dim > 3) {
            a = pdata[index+3];
        }
        if (!isVisible) {
            a = 0;
        }
        return (int4)(r, g, b, a);
    }

    int4 getPixelF(__global uchar *pdata, float xF, float yF, int h, int w, int dim, int offset) {
        if (xF < -1.0) { xF = -1.0; }
        if (yF < -1.0) { yF = -1.0; }
        if (xF > (float)(w+1)) { xF = (float)(w+1); }
        if (yF > (float)(h+1)) { yF = (float)(h+1); }

        int x0 = (int) floor(xF);
        int x1 = (int) ceil(xF);
        float xLerp = xF - (float) x0;
        int y0 = (int) floor(yF);
        int y1 = (int) ceil(yF);
        float yLerp = yF - (float) y0;

        xLerp = 1.0 - xLerp;
        yLerp = 1.0 - yLerp;

        int4 colorTL = getPixel(pdata, x0, y0, h, w, dim, offset);
        int4 colorTR = getPixel(pdata, x1, y0, h, w, dim, offset);
        int4 colorBL = getPixel(pdata, x0, y1, h, w, dim, offset);
        int4 colorBR = getPixel(pdata, x1, y1, h, w, dim, offset);

        int4 colorT = blendColors(colorTL, colorTR, xLerp);
        int4 colorB = blendColors(colorBL, colorBR, xLerp);

        int4 finalcolor = blendColors(colorT, colorB, yLerp);

        // avoid dark corners
        if (colorT.w < 255 && colorB.w < 255) {
            finalcolor.w = max(colorT.w, colorB.w);
        }

        return finalcolor;
    }

    __kernel void makeImage(__global uchar *pdata, __global int *props, __global int *zvalues, __global uchar *result){
        int canvasW = %d;
        int canvasH = %d;
        int i = get_global_id(0);
        int pcount = %d;
        int colorDimensions = %d;
        int precisionMultiplier = %d;
        int offset = props[i*pcount];
        float xF = (float) props[i*pcount+1] / (float) precisionMultiplier;
        float yF = (float) props[i*pcount+2] / (float) precisionMultiplier;
        int x = (int) floor(xF);
        int y = (int) floor(yF);
        float remainderX = xF - (float) x;
        float remainderY = yF - (float) y;
        int w = props[i*pcount+3];
        int h = props[i*pcount+4];
        float twF = (float) props[i*pcount+5] / (float) precisionMultiplier;
        float thF = (float) props[i*pcount+6] / (float) precisionMultiplier;
        float remainderW = (remainderX+twF) - floor(remainderX+twF);
        float remainderH = (remainderY+thF) - floor(remainderY+thF);
        //int tw = (int) ceil(twF);
        //int th = (int) ceil(thF);
        int tw = (int) ceil(remainderX+twF);
        int th = (int) ceil(remainderY+thF);
        int alpha = props[i*pcount+7];
        int zdindex = props[i*pcount+8];
        float falpha = (float) alpha / (float) 255.0;

        //printf(" %%d ", tw);
        //printf(" %%d ", th);

        for (int row=0; row<th; row++) {
            for (int col=0; col<tw; col++) {
                int dstX = col + x;
                int dstY = row + y;

                float srcNX = norm((float) col, remainderX, remainderX+twF-1.0);
                float srcNY = norm((float) row, remainderY, remainderY+thF-1.0);
                float srcXF = srcNX * (float) (w-1);
                float srcYF = srcNY * (float) (h-1);
                //float srcXF = norm((float) col, remainderX, remainderX+twF) * (float) (w-1);
                //float srcYF = norm((float) row, remainderY, remainderY+thF) * (float) (h-1);

                if (srcNX < 0.0) { srcXF = -remainderX; }
                if (srcNY < 0.0) { srcYF = -remainderY; }
                if (srcNX > 1.0) { srcXF = (float) (w-1) + (1.0-remainderW); }
                if (srcNY > 1.0) { srcYF = (float) (h-1) + (1.0-remainderH); }

                // printf("(%%f,%%f) ", srcXF, srcYF);

                if (dstX >= 0 && dstX < canvasW && dstY >= 0 && dstY < canvasH) {
                    int4 srcColor = getPixelF(pdata, srcXF, srcYF, h, w, colorDimensions, offset);
                    int destIndex = dstY * canvasW * 3 + dstX * 3;
                    int destZIndex = dstY * canvasW + dstX;
                    int destZValue = zvalues[dstY * canvasW + dstX];
                    // r, g, b, a = x, y, z, w
                    // if alpha is greater than zero and z-index is lower than existing (if applicable)
                    if (srcColor.w > 0 && (destZValue <= 0 || destZValue < zdindex)) {
                        float talpha = (float) srcColor.w / (float) 255.0 * falpha;
                        float invalpha = 1.0 - talpha;
                        // mix the existing color with new color
                        int dr = result[destIndex];
                        int dg = result[destIndex+1];
                        int db = result[destIndex+2];
                        result[destIndex] = (int) round(((float) srcColor.x * talpha) + ((float) dr * invalpha));
                        result[destIndex+1] = (int) round(((float) srcColor.y * talpha) + ((float) dg * invalpha));
                        result[destIndex+2] = (int) round(((float) srcColor.z * talpha) + ((float) db * invalpha));
                        zvalues[destZIndex] = zdindex;
                    }
                }
            }
            // printf("\\n");
        }
    }
    """ % (width, height, pcount, colorDimensions, precisionMultiplier)

    ctx, mf, queue, prg = loadGPUProgram(srcCode)

    bufIn1 =  cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=flatPixelData)
    bufIn2 =  cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=properties)
    bufInZ = cl.Buffer(ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=zvalues)
    bufOut = cl.Buffer(ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=result)
    prg.makeImage(queue, (count, ), None , bufIn1, bufIn2, bufInZ, bufOut)

    # Copy result
    cl.enqueue_copy(queue, result, bufOut)
    result = result.reshape(height, width, 3)
    return result


def loadGPUProgram(srcCode):
    # Get platforms, both CPU and GPU
    plat = cl.get_platforms()
    GPUs = plat[0].get_devices(device_type=cl.device_type.GPU)
    CPU = plat[0].get_devices()
    # prefer GPUs
    if GPUs and len(GPUs) > 0:
        ctx = cl.Context(devices=GPUs)
    else:
        print("Warning: using CPU instead of GPU")
        ctx = cl.Context(CPU)
    # Create queue for each kernel execution
    queue = cl.CommandQueue(ctx)
    mf = cl.mem_flags
    # Kernel function instantiation
    prg = cl.Program(ctx, srcCode).build()

    return (ctx, mf, queue, prg)
