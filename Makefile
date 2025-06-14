# Makefile for CUDA ECDSA verification library

NVCC = nvcc
NVCC_FLAGS = -O3 -arch=sm_75 -shared -Xcompiler -fPIC --ptxas-options=-v -lineinfo
CUDA_INCLUDES = -I/usr/local/cuda/include
CUDA_LIBS = -L/usr/local/cuda/lib64 -lcudart

# Target library
TARGET = libcuda_ecdsa.so
SOURCE = cuda_ecdsa.cu

# Default target
all: $(TARGET)

# Build the shared library
$(TARGET): $(SOURCE)
	$(NVCC) $(NVCC_FLAGS) $(CUDA_INCLUDES) -o $@ $< $(CUDA_LIBS)

# Clean build artifacts
clean:
	rm -f $(TARGET)

# Install to system library path
install: $(TARGET)
	cp $(TARGET) /usr/local/lib/
	ldconfig

.PHONY: all clean install