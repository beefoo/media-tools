# -*- coding: utf-8 -*-

import argparse
import inspect
import math
import numpy as np
import os
from PIL import Image
from pprint import pprint
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from lib.audio_mixer import *
from lib.audio_utils import *
from lib.cache_utils import *
from lib.clip import *
from lib.collection_utils import *
from lib.composition_utils import *
from lib.gpu_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.processing_utils import *
from lib.sampler import *
from lib.statistics_utils import *
from lib.video_utils import *

# input
parser = argparse.ArgumentParser()
addVideoArgs(parser)
parser.add_argument('-grid', dest="GRID", default="128x128", help="Size of grid")
parser.add_argument('-grid0', dest="START_GRID", default="128x128", help="Start size of grid")
parser.add_argument('-grid1', dest="END_GRID", default="128x128", help="End size of grid")
parser.add_argument('-volr', dest="VOLUME_RANGE", default="0.4,0.8", help="Volume range")
parser.add_argument('-cdur', dest="CYCLE_MS", default=16000, type=int, help="Duration of cycle in milliseconds")
parser.add_argument('-cycles', dest="CYCLES", default=3.875, type=float, help="Number of cycles")
parser.add_argument('-coffset', dest="CYCLE_OFFSET", default=0.125, type=float, help="Number of cycles to offset")
a = parser.parse_args()
parseVideoArgs(a)
aa = vars(a)

# Get video data
startTime = logTime()
stepTime = startTime
samples, sampleCount, container, sampler, stepTime, cCol, cRow, gridW, gridH, startGridW, startGridH, endGridW, endGridH = initGridComposition(a, stepTime)

# set clip brightness to min by default
for i, s in enumerate(samples):
    samples[i]["brightness"] = a.BRIGHTNESS_RANGE[0]

clips = samplesToClips(samples)
stepTime = logTime(stepTime, "Samples to clips")

startMs = a.PAD_START
cycleMs = roundInt(a.CYCLE_MS * a.CYCLES)
cycleOffsetMs = roundInt(a.CYCLE_MS * a.CYCLE_OFFSET)
cyclesMs = cycleMs + cycleOffsetMs
endMs = startMs + cyclesMs
distanceToMove = roundInt(a.WIDTH * a.CYCLES)
durationMs = endMs

# clipW = clips[0].props["width"]
# clipH = clips[0].props["height"]
# clipMargin = a.CLIP_MARGIN * clipW

stepTime = logTime(stepTime, "Calculated sequence")

def postProcessSlice(im, ms):
    global a
    global startMs
    global distanceToMove
    global cycleMs
    global cycleOffsetMs

    pixels = np.array(im, dtype=np.uint8)
    colors = 3
    height, width, _ = pixels.shape
    pixels = pixels.reshape(-1)
    result = np.zeros(height * width * colors, dtype=np.uint8)

    # the kernel function
    srcCode = """
    static float ease(float value) {
        float n = value;
        if (n < 0.5) {
            n = 2.0 * n * n;
        } else {
            n = -1.0 + (4.0 - 2.0 * n) * n;
        }
        return n;
    }

    static float easeBell(float value) {
        float n = value;
        if (n < 0.5) {
            n = ease(n / 0.5);
        } else {
            n = 1.0 - ease((n - 0.5) / 0.5);
        }
        return n;
    }

    static float normF(float value, float a, float b) {
        float n = (value - a) / (b - a);
        if (n > 1.0) n = 1.0;
        if (n < 0.0) n = 0.0;
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

    int4 getPixel(__global uchar *pdata, int x, int y, int h, int w, int dim);
    int4 getPixelF(__global uchar *pdata, float xF, float yF, int h, int w, int dim);

    int4 getPixel(__global uchar *pdata, int x, int y, int h, int w, int dim) {
        // check bounds; retain rgb color of edge, but make alpha=0
        bool isVisible = true;
        if (x < 0) { isVisible = false; x = 0; }
        if (y < 0) { isVisible = false; y = 0; }
        if (x >= w) { isVisible = false; x = w-1; }
        if (y >= h) { isVisible = false; y = h-1; }

        int index = y * w * dim + x * dim;
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

    int4 getPixelF(__global uchar *pdata, float xF, float yF, int h, int w, int dim) {
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

        int4 colorTL = getPixel(pdata, x0, y0, h, w, dim);
        int4 colorTR = getPixel(pdata, x1, y0, h, w, dim);
        int4 colorBL = getPixel(pdata, x0, y1, h, w, dim);
        int4 colorBR = getPixel(pdata, x1, y1, h, w, dim);

        int4 colorT = blendColors(colorTL, colorTR, xLerp);
        int4 colorB = blendColors(colorBL, colorBR, xLerp);
        int4 finalcolor = blendColors(colorT, colorB, yLerp);

        return finalcolor;
    }

    __kernel void sliceImage(__global uchar *pdata, __global uchar *result){
        int canvasW = %d;
        int canvasH = %d;
        int colorDimensions = %d;
        float ms = %f;
        float startMs = %f;
        float distanceToMove = %f;
        float cycleMs = %f;
        float cycleOffsetMs = %f;

        // get current position
        int posx = get_global_id(1);
        int posy = get_global_id(0);
        int i = posy * canvasW * colorDimensions + posx * colorDimensions;

        // make vertical middle values move earlier/faster
        float ny = (float) posy / (float) (canvasH-1);
        ny = 1.0 - easeBell(ny); // middle y values are near 0.0
        float offsetMs = cycleOffsetMs * ny;
        float cycleStartMs = startMs+offsetMs;
        float nprogress = normF(ms, cycleStartMs, cycleStartMs + cycleMs);
        nprogress = ease(nprogress);
        float offsetX = nprogress * distanceToMove;
        if (posy %% 2 > 0) offsetX = -offsetX;
        float xf = (float) posx + offsetX;
        xf = fmod(xf, (float) canvasW); // wrap around
        if (xf < 0.0) xf = (float) canvasW + xf;

        // get srcPixel
        int4 srcColor = getPixelF(pdata, xf, (float) posy, canvasH, canvasW, colorDimensions);
        float salpha = 1.0;
        // slowly fade out second half
        if (nprogress > 0.5) {
            salpha = 1.0 - ((nprogress-0.5)/0.5);
        }

        // write dest pixel
        int4 destColor = (int4)(0, 0, 0, 255);
        int4 blendedColor = blendColors(srcColor, destColor, salpha);
        result[i] = blendedColor.x;
        result[i+1] = blendedColor.y;
        result[i+2] = blendedColor.z;
    }
    """ % (width, height, colors, ms, startMs, distanceToMove, cycleMs, cycleOffsetMs)

    ctx, prg = loadGPUProgram(srcCode)
    # Create queue for each kernel execution
    queue = cl.CommandQueue(ctx)
    mf = cl.mem_flags

    bufIn =  cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=pixels)
    bufOut = cl.Buffer(ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=result)
    prg.sliceImage(queue, (height, width), None , bufIn, bufOut)

    # Copy result
    cl.enqueue_copy(queue, result, bufOut)
    result = result.reshape(height, width, colors)

    im = Image.fromarray(result, mode="RGB")
    return im

processComposition(a, clips, durationMs, sampler, stepTime, startTime, postProcessingFunction=postProcessSlice)
