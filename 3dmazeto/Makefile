OBJS   = read_res.o write_tga.o main.o
TARGET = 3dmazeto
CFLAGS = -pedantic -Wall -Wextra -std=gnu99

$(TARGET): $(OBJS)
	$(CC) $(LDFLAGS) -o $(TARGET) $(OBJS)

all: $(TARGET)

clean:
	rm -f $(TARGET) $(OBJS)

.PHONY: clean
