# -*- coding: utf-8 -*-

import numpy as np
import os
from pprint import pprint
import pyopencl as cl

os.environ['PYOPENCL_COMPILER_OUTPUT'] = '1'

def clipsToImageGPU(width, height, pixelData, properties):
    count = len(pixelData)
    pixelData = np.array(pixelData).reshape(-1)
    properties = np.array(properties).reshape(-1)

    pixelData = pixelData.astype(np.uint8)
    properties = properties.astype(np.int32)
    result = np.zeros(width * height * 3, dtype=np.uint8)

    # the kernel function
    srcCode = """
    __kernel void makeImage(__global uchar *pdata, __global int *props, __global uchar *result){
        int canvasW = %d;
        int canvasH = %d;
        int i = get_global_id(0);
        int pcount = 8;
        int offset = props[i*pcount];
        int x = props[i*pcount+1];
        int y = props[i*pcount+2];
        int w = props[i*pcount+3];
        int h = props[i*pcount+4];
        int tw = props[i*pcount+5];
        int th = props[i*pcount+6];
        int alpha = props[i*pcount+7];
        float falpha = (float) alpha / (float) 255.0;

        bool isScaled = (w != tw || h != th);

        for (int trow=0; trow<th; trow++) {
            for (int tcol=0; tcol<tw; tcol++) {
                int row = trow;
                int col = tcol;
                if (isScaled) {
                    row = (int) round(((float) trow / (float) (th-1)) * (float) (h-1));
                    col = (int) round(((float) tcol / (float) (tw-1)) * (float) (w-1));
                }
                int px = x + col;
                int py = y + row;
                if (px >= 0 && px < canvasW && py >= 0 && py < canvasH) {
                    int srcIndex = trow * tw * 3 + tcol * 3 + offset;
                    int destIndex = py * canvasW * 3 + px * 3;
                    int r = pdata[srcIndex];
                    int g = pdata[srcIndex+1];
                    int b = pdata[srcIndex+2];
                    result[destIndex] = (int) round((float) r * falpha);
                    result[destIndex+1] = (int) round((float) g * falpha);
                    result[destIndex+2] = (int) round((float) b * falpha);
                }
            }
        }
    }
    """ % (width, height)

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

    bufIn1 =  cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=pixelData)
    bufIn2 =  cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=properties)
    bufOut = cl.Buffer(ctx, mf.WRITE_ONLY, result.nbytes)
    prg.makeImage(queue, (count, ), None , bufIn1, bufIn2, bufOut)

    # Copy result
    cl.enqueue_copy(queue, result, bufOut)
    result = result.reshape(height, width, 3)
    return result
