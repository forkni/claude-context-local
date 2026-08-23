// Tiny CUDA fixture: device helper, global kernel, constant, host launcher.

__device__ float square(float x) {
    return x * x;
}

__global__ void computeSquares(const float* input, float* output, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < n) {
        output[idx] = square(input[idx]);
    }
}

__constant__ float kScaleFactor = 2.0f;

// Host launcher with a triple-chevron kernel launch -- not valid C++ token
// syntax, exercises the CudaChunker-only _LAUNCH_CFG blanking pass.
void launchComputeSquares(const float* input, float* output, int n) {
    int threads = 256;
    int blocks = (n + threads - 1) / threads;
    computeSquares<<<blocks, threads>>>(input, output, n);
}
