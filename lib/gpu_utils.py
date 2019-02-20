# -*- coding: utf-8 -*-

import numpy as np
import os
from pprint import pprint
import sys

# Don't require pyopencl to be installed, but it will throw error if we try to use it and it doesn't exist
try:
    import pyopencl as cl
    os.environ['PYOPENCL_COMPILER_OUTPUT'] = '1'

except ImportError:
    print("Warning: no PyOpenCL detected, so no GPU-accellerated processing available")

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
    zvalues = np.zeros(width * height, dtype=np.int32)
    result = np.zeros(width * height * 3, dtype=np.uint8)

    # the kernel function
    srcCode = """
    int4 getPixel(__global uchar *pdata, int x, int y, int h, int w, int dim, int offset);

    int4 getPixel(__global uchar *pdata, int x, int y, int h, int w, int dim, int offset) {
        if (x < 0 || y < 0 || x >= w || y >= h) {
            return (int4)(0, 0, 0, 0);
        }
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

    __kernel void makeImage(__global uchar *pdata, __global int *props, __global int *zvalues, __global uchar *result){
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
        int zdindex = props[i*pcount+8];
        float falpha = (float) alpha / (float) 255.0;
        bool isScaled = (w != tw || h != th);

        for (int row=0; row<th; row++) {
            for (int col=0; col<tw; col++) {
                int srcX = col;
                int srcY = row;
                int dstX = col;
                int dstY = row;
                if (isScaled) {
                    srcX = (int) round(((float) dstX / (float) (tw-1)) * (float) (w-1));
                    srcY = (int) round(((float) dstY / (float) (th-1)) * (float) (h-1));
                }
                dstX = dstX + x;
                dstY = dstY + y;
                if (dstX >= 0 && dstX < canvasW && dstY >= 0 && dstY < canvasH) {
                    int4 srcColor = getPixel(pdata, srcX, srcY, h, w, colorDimensions, offset);
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
        print("Warning: using CPU instead of GPU")
        ctx = cl.Context(CPU)
    # Create queue for each kernel execution
    queue = cl.CommandQueue(ctx)
    mf = cl.mem_flags
    # Kernel function instantiation
    prg = cl.Program(ctx, srcCode).build()

    bufIn1 =  cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=flatPixelData)
    bufIn2 =  cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=properties)
    bufInZ = cl.Buffer(ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=zvalues)
    bufOut = cl.Buffer(ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=result)
    prg.makeImage(queue, (count, ), None , bufIn1, bufIn2, bufInZ, bufOut)

    # Copy result
    cl.enqueue_copy(queue, result, bufOut)
    result = result.reshape(height, width, 3)
    return result
