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
        int offset = props[i*6];
        int x = props[i*6+1];
        int y = props[i*6+2];
        int w = props[i*6+3];
        int h = props[i*6+4];
        int alpha = props[i*6+5];
        float falpha = (float) alpha / (float) 255.0;

        for (int row=0; row<h; row++) {
            for (int col=0; col<w; col++) {
                int px = x + col;
                int py = y + row;
                if (px >= 0 && px < canvasW && py >= 0 && py < canvasH) {
                    int srcIndex = row * w * 3 + col * 3 + offset;
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
