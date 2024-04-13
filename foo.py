import socket


def create_startup_packet(
    user: str = "testuser",
    database: str = "testdb",
) -> bytes:
    # Start with protocol version number: 3.0
    packet = bytearray([0x00, 0x03, 0x00, 0x00])

    # Add parameter pairs, each pair followed by null terminator
    parameters = [
        ("user", user),
        ("database", database),
        ("replication", "database"),
        # You can add more parameters here as needed
    ]
    for param, value in parameters:
        packet.extend(f"{param}\x00{value}\x00".encode("utf-8"))

    # Add a final null byte to indicate the end of parameter entries
    packet.append(0x00)

    # Prepend length of the packet including the length field itself
    length = len(packet) + 4  # 4 bytes for the length field
    packet = bytearray(length.to_bytes(4, "big")) + packet

    return bytes(packet)


def make_query(query: str) -> bytes:
    length = len(query) + 1 + 4  # query length + null byte + 4 bytes for length
    return (
        b"Q" + (length).to_bytes(4, byteorder="big") + query.encode("utf-8") + b"\x00"
    )


def connect() -> None:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("127.0.0.1", 5432))
    print(s)

    s.sendall(create_startup_packet())
    recved = s.recv(2**12)
    print(recved)
    print(recved.decode(errors="ignore"))

    start_replication_command = make_query("START_REPLICATION SLOT test LOGICAL 0/0;")
    print(start_replication_command)
    s.sendall(start_replication_command)
    recved = s.recv(2**12)
    print(recved)
    print(recved.decode(errors="ignore"))

    print("Enter while loop.")
    while True:
        if recved := s.recv(2**12):
            print(recved.decode(errors="ignore"))


def main() -> None:
    connect()


if __name__ == "__main__":
    main()
