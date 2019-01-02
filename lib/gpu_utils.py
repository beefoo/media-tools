# -*- coding: utf-8 -*-

import numpy as np
import os
from pprint import pprint
import pyopencl as cl

os.environ['PYOPENCL_COMPILER_OUTPUT'] = '1'

def clipsToImageGPU(width, height, pixelData, properties, colorDimensions):
    count = len(pixelData)
    flatPixelData = []
    isUniform = np.array(pixelData).ndim > 1
    if isUniform:
        flatPixelData = np.array(pixelData).reshape(-1)
    else:
        for d in pixelData:
            flatPixelData += list(d.reshape(-1))
        flatPixelData = np.array(flatPixelData)
    pcount = len(properties[0])
    properties = np.array(properties).reshape(-1)
    flatPixelData = flatPixelData.astype(np.uint8)
    properties = properties.astype(np.int32)
    result = np.zeros(width * height * 3, dtype=np.uint8)

    # the kernel function
    # rotation with bilinear interpolation = http://polymathprogrammer.com/2008/10/06/image-rotation-with-bilinear-interpolation/
    srcCode = """

    static float2 rotatePixel(int x, int y, int cx, int cy, float angle) {
        float rad = radians(angle);
        float s = sin(rad);
        float c = cos(rad);

        x = x - cx;
        y = y - cy;

        float xNew = (float) x * c - (float) y * s;
        float yNew = (float) x * s + (float) y * c;

        xNew = xNew + (float) cx;
        yNew = yNew + (float) cy;

        return (float2)(xNew, yNew);
    }

    int4 getPixel(__global uchar *pdata, int x, int y, int w, int dim, int offset);
    int4 interpolateColor(__global uchar *pdata, float2 pos, int h, int w, int dim, int offset);

    int4 getPixel(__global uchar *pdata, int x, int y, int w, int dim, int offset) {
        int index = y * w * dim + x * dim + offset;
        int r = pdata[index];
        int g = pdata[index+1];
        int b = pdata[index+2];
        int a = 255;
        if (dim > 3) {
            a = pdata[index+3];
        }
        return (int4)(r, g, b, a);
    }

    int4 interpolateColor(__global uchar *pdata, float2 pos, int h, int w, int dim, int offset) {
        float trueX = pos.x;
        float trueY = pos.y;

        int floorX = (int) floor(trueX);
        int floorY = (int) floor(trueY);
        int ceilX = (int) ceil(trueX);
        int ceilY = (int) ceil(trueY);

        // check bounds
        if (ceilX < 0 || floorX >= w || ceilY < 0 || floorY >= h) {
            return (int4)(0, 0, 0, 0);
        }

        float deltaX = trueX - (float)floorX;
        float deltaY = trueY - (float)floorY;

        // no interpolation necessary
        if (deltaX == 0.0 && deltaY == 0.0) {
            return getPixel(pdata, floorX, floorY, w, dim, offset);
        }

        int4 clrTopLeft = (int4)(0, 0, 0, 0);
        int4 clrTopRight = (int4)(0, 0, 0, 0);
        int4 clrBottomLeft = (int4)(0, 0, 0, 0);
        int4 clrBottomRight = (int4)(0, 0, 0, 0);

        if (floorX >= 0 && floorX < w && floorY >= 0 && floorY < h) {
            clrTopLeft = getPixel(pdata, floorX, floorY, w, dim, offset);
        }
        if (ceilX >= 0 && ceilX < w && floorY >= 0 && floorY < h) {
            clrTopRight = getPixel(pdata, ceilX, floorY, w, dim, offset);
        }
        if (floorX >= 0 && floorX < w && ceilY >= 0 && ceilY < h) {
            clrBottomLeft = getPixel(pdata, floorX, ceilY, w, dim, offset);
        }
        if (ceilX >= 0 && ceilX < w && ceilY >= 0 && ceilY < h) {
            clrBottomRight = getPixel(pdata, ceilX, ceilY, w, dim, offset);
        }

        // linearly interpolate horizontally between top neighbours
        float fTopR = (1.0 - deltaX) * (float)clrTopLeft.r + deltaX * (float)clrTopRight.r;
        float fTopG = (1.0 - deltaX) * (float)clrTopLeft.g + deltaX * (float)clrTopRight.g;
        float fTopB = (1.0 - deltaX) * (float)clrTopLeft.b + deltaX * (float)clrTopRight.b;
        float fTopA = (1.0 - deltaX) * (float)clrTopLeft.a + deltaX * (float)clrTopRight.a;

        // linearly interpolate horizontally between bottom neighbours
        float fBottomR = (1.0 - deltaX) * (float)clrBottomLeft.r + deltaX * (float)clrBottomRight.r;
        float fBottomG = (1.0 - deltaX) * (float)clrBottomLeft.g + deltaX * (float)clrBottomRight.g;
        float fBottomB = (1.0 - deltaX) * (float)clrBottomLeft.b + deltaX * (float)clrBottomRight.b;
        float fBottomA = (1.0 - deltaX) * (float)clrBottomLeft.a + deltaX * (float)clrBottomRight.a;

        // linearly interpolate vertically between top and bottom interpolated results
        int r = (int)round((float)(1.0 - deltaY) * fTopR + deltaY * fBottomR);
        int g = (int)round((float)(1.0 - deltaY) * fTopG + deltaY * fBottomG);
        int b = (int)round((float)(1.0 - deltaY) * fTopB + deltaY * fBottomB);
        int a = (int)round((float)(1.0 - deltaY) * fTopA + deltaY * fBottomA);

        return (int4)(r, g, b, a);
    }

    __kernel void makeImage(__global uchar *pdata, __global int *props, __global uchar *result){
        int canvasW = %d;
        int canvasH = %d;
        int i = get_global_id(0);
        int pcount = %d;
        int colorDimensions = %d;
        int offset = props[i*pcount];
        int x = props[i*pcount+1];
        int y = props[i*pcount+2];
        int w = props[i*pcount+3];
        int h = props[i*pcount+4];
        int tw = props[i*pcount+5];
        int th = props[i*pcount+6];
        int alpha = props[i*pcount+7];
        float falpha = (float) alpha / (float) 255.0;
        float rotation = (float) props[i*pcount+8] / (float) 1000.0;
        float blur = (float) props[i*pcount+9] / (float) 1000.0;
        bool isScaled = (w != tw || h != th);

        int cx = (int) round((float) w * (float) 0.5);
        int cy = (int) round((float) h * (float) 0.5);
        int diagonal = (int) ceil((float) sqrt((float)tw * (float)tw + (float)th * (float)th)); // iterate over diagonal to account for rotation
        int dx = (int) round((float)(diagonal - tw) * (float) 0.5);
        int dy = (int) round((float)(diagonal - th) * (float) 0.5);

        for (int i=0; i<diagonal; i++) {
            for (int j=0; j<diagonal; j++) {
                int srcX = j - dx;
                int srcY = i - dy;
                int dstX = j - dx;
                int dstY = i - dy;
                if (isScaled) {
                    srcX = (int) round(((float) dstX / (float) (tw-1)) * (float) (w-1));
                    srcY = (int) round(((float) dstY / (float) (th-1)) * (float) (h-1));
                }
                dstX = dstX + x;
                dstY = dstY + y;
                float2 fSrc = (float2)((float) srcX, (float) srcY);
                if (rotation > 0.0) {
                    fSrc = rotatePixel(srcX, srcY, cx, cy, -rotation);
                }
                if (dstX >= 0 && dstX < canvasW && dstY >= 0 && dstY < canvasH && fSrc.x >= 0.0 && fSrc.x < (float)w && fSrc.y >= 0.0 && fSrc.y < (float)h) {
                    int4 srcColor = interpolateColor(pdata, fSrc, h, w, colorDimensions, offset);
                    int destIndex = dstY * canvasW * 3 + dstX * 3;
                    if (srcColor.a > 0) {
                        float talpha = (float) srcColor.a / (float) 255.0 * falpha;
                        result[destIndex] = (int) round((float) srcColor.r * talpha);
                        result[destIndex+1] = (int) round((float) srcColor.g * talpha);
                        result[destIndex+2] = (int) round((float) srcColor.b * talpha);
                    }
                }
            }
        }
    }
    """ % (width, height, pcount, colorDimensions)

    # Get platforms, both CPU and GPU
    plat = cl.get_platforms()
    GPUs = plat[0].get_devices(device_type=cl.device_type.GPU)
    CPU = plat[0].get_devices()
    # prefer GPUs
    if GPUs and len(GPUs) > 0:
        ctx = cl.Context(devices=GPUs)
    else:
        print "Warning: using CPU instead of GPU"
        ctx = cl.Context(CPU)
    # Create queue for each kernel execution
    queue = cl.CommandQueue(ctx)
    mf = cl.mem_flags
    # Kernel function instantiation
    prg = cl.Program(ctx, srcCode).build()

    bufIn1 =  cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=flatPixelData)
    bufIn2 =  cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=properties)
    bufOut = cl.Buffer(ctx, mf.WRITE_ONLY, result.nbytes)
    prg.makeImage(queue, (count, ), None , bufIn1, bufIn2, bufOut)

    # Copy result
    cl.enqueue_copy(queue, result, bufOut)
    result = result.reshape(height, width, 3)
    return result
