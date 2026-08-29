# 编译器设置
CXX = g++
# 编译标志：
# -O3: 开启最高级别优化，对密集循环至关重要
# -std=c++11: 支持 stoul 等 C++11 特性
# -Wall: 开启常用警告
CXXFLAGS = -O3 -std=c++11 -Wall

# 目标可执行文件名
TARGET = computecor

# 源文件
SRC = computecor.cpp

# 默认目标
all: $(TARGET)

# 编译规则
$(TARGET): $(SRC)
	@echo "Compiling $(SRC) with high optimization (-O3)..."
	$(CXX) $(CXXFLAGS) -o $(TARGET) $(SRC)
	@echo "Build successful! Run using: ./$(TARGET)"

# 清理规则
clean:
	@echo "Cleaning up..."
	rm -f $(TARGET)
	@echo "Clean done."

# 方便运行的命令 (可选)
run: $(TARGET)
	./$(TARGET)

# 声明伪目标
.PHONY: all clean run
