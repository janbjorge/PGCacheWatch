import struct

# print(int.from_bytes(b"\x00\x00\x00\x08", "big"))
print(struct.unpack("!cII", b"R\x00\x00\x00\x08\x00\x00\x00\x00"))
