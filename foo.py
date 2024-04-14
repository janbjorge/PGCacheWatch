import socket
import struct
from dataclasses import dataclass
from typing import Generator


@dataclass
class Header:
    type: str
    length: int

    @staticmethod
    def from_bytes(raw: bytes) -> "Header":
        type, length = struct.unpack("!cI", raw[:5])
        return Header(
            type=type.decode(),
            length=length,
        )


@dataclass
class AuthenticationOk:
    auth_code: int

    @staticmethod
    def from_bytes(raw: bytes) -> "AuthenticationOk":
        *_, auth_code = struct.unpack("!cII", raw)
        return AuthenticationOk(auth_code=auth_code)


@dataclass
class BackendKeyData:
    process_id: int
    secret_key: int

    @staticmethod
    def from_bytes(raw: bytes) -> "BackendKeyData":
        *_, pid, key = struct.unpack("!cIII", raw)
        return BackendKeyData(process_id=pid, secret_key=key)


@dataclass
class ParameterStatus:
    name: str
    value: str

    @staticmethod
    def from_bytes(raw: bytes) -> "ParameterStatus":
        # Skip header first 5, ignore null termination.
        name, value = raw[5:-1].split(b"\x00", maxsplit=2)
        return ParameterStatus(
            name=name.decode(),
            value=value.decode(),
        )


@dataclass
class ReadyForQuery:
    status: str

    @staticmethod
    def from_bytes(raw: bytes) -> "ReadyForQuery":
        *_, status = struct.unpack("!cIc", raw)
        return ReadyForQuery(status=status.decode())


@dataclass
class CopyData:
    data: bytes

    @staticmethod
    def from_bytes(raw: bytes) -> "CopyData":
        return CopyData(data=raw[5:])


@dataclass
class XLogData:
    type: str
    start: int
    stop: int
    clock: int
    data: bytes

    @staticmethod
    def from_bytes(raw: bytes) -> "XLogData":
        cqqq_len = 1 + 3 * 8
        type, start, stop, clock = struct.unpack("!cqqq", raw[:cqqq_len])
        return XLogData(
            type=type.decode(),
            start=start,
            stop=stop,
            clock=clock,
            data=raw[cqqq_len:],
        )


@dataclass
class PrimaryKeepaliveMessage:
    type: str
    wal_end: int
    clock: int
    high_urgency: int

    @staticmethod
    def from_bytes(raw: bytes) -> "PrimaryKeepaliveMessage":
        type, wal_end, clock, high_urgency = struct.unpack("!cqqb", raw)
        return PrimaryKeepaliveMessage(
            type=type,
            wal_end=wal_end,
            clock=clock,
            high_urgency=high_urgency,
        )


def create_standby_status_update(
    wal_receive_lsn: int,
    wal_flush_lsn: int,
    wal_apply_lsn: int,
    wal_time: int,
    reply_requested: int = 0,
) -> bytes:
    # Define the message type for a Standby Status Update
    message_type = b"r"

    # Pack the data into a binary format
    # '!cQQQQB' stands for:
    # - '!': network byte order (big-endian)
    # - 'c': char (1 byte) for the message type
    # - 'Q': unsigned long long (8 bytes) for each WAL location and the timestamp
    # - 'B': unsigned char (1 byte) for the reply request flag
    packet_format = "!cQQQQB"
    return struct.pack(
        packet_format,
        message_type,
        wal_receive_lsn,
        wal_flush_lsn,
        wal_apply_lsn,
        wal_time,
        reply_requested,
    )


def create_copy_data(data: bytes) -> bytes:
    return b"d" + bytearray((len(data) + 4).to_bytes(4, "big")) + data


def sequence_split_at(seq: bytes, idx: int) -> tuple[bytes, bytes]:
    left = seq[:idx]
    right = seq[idx:]
    return left, right


def parse(sequence: bytes) -> Generator:
    while sequence:
        header = Header.from_bytes(sequence)
        to_parse, sequence = sequence_split_at(sequence, header.length + 1)

        match header.type:
            case "R":
                yield AuthenticationOk.from_bytes(to_parse)
            case "S":
                yield ParameterStatus.from_bytes(to_parse)
            case "K":
                yield BackendKeyData.from_bytes(to_parse)
            case "Z":
                yield ReadyForQuery.from_bytes(to_parse)
            case "W":
                ...
            case "d":
                yield CopyData.from_bytes(to_parse)
            case _:
                raise NotImplementedError(header)


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


def connect(s: socket.socket) -> None:
    s.connect(("127.0.0.1", 5432))
    print(s)

    s.sendall(create_startup_packet())
    recved = s.recv(2**20)
    for x in parse(recved):
        print(x)

    start_replication_command = make_query(
        "START_REPLICATION SLOT test LOGICAL 0/1EA8208"
    )
    s.sendall(start_replication_command)
    recved = s.recv(2**20)
    for x in parse(recved):
        print(x)

    print("Enter while loop.")
    while True:
        if recved := s.recv(4096):
            for x in parse(recved):
                if isinstance(x, CopyData):
                    match chr(x.data[0]):
                        case "k":
                            pkam = PrimaryKeepaliveMessage.from_bytes(x.data)
                            print(pkam)
                            s.sendall(
                                create_copy_data(
                                    create_standby_status_update(
                                        pkam.wal_end + 1,
                                        pkam.wal_end + 1,
                                        pkam.wal_end + 1,
                                        pkam.clock,
                                    )
                                )
                            )
                        case "w":
                            print(XLogData.from_bytes(x.data))
                        case _:
                            raise NotImplementedError(x)


def main() -> None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            connect(s)
    finally:
        s.close()


if __name__ == "__main__":
    main()
