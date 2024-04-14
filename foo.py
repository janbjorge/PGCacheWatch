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
    header: Header
    auth_code: int

    @staticmethod
    def from_bytes(raw: bytes, header: Header) -> "AuthenticationOk":
        *_, auth_code = struct.unpack("!cII", raw)
        return AuthenticationOk(
            header=header,
            auth_code=auth_code,
        )


@dataclass
class BackendKeyData:
    header: Header
    process_id: int
    secret_key: int

    @staticmethod
    def from_bytes(raw: bytes, header: Header) -> "BackendKeyData":
        *_, pid, key = struct.unpack("!cIII", raw)
        return BackendKeyData(header=header, process_id=pid, secret_key=key)


@dataclass
class ParameterStatus:
    header: Header
    name: str
    value: str

    @staticmethod
    def from_bytes(raw: bytes, header: Header) -> "ParameterStatus":
        strings_data = raw[5:]
        null_index = strings_data.find(b"\x00")
        if null_index == -1:
            raise ValueError("Parameter name is not null-terminated.")

        # Extract parameter name
        param_name = strings_data[:null_index].decode("utf-8")

        # Remove the parameter name and the null byte from the strings_data
        strings_data = strings_data[null_index + 1 :]

        # Find the next null byte for the parameter value
        null_index = strings_data.find(b"\x00")
        if null_index == -1:
            raise ValueError("Parameter value is not null-terminated.")

        # Extract parameter value
        param_value = strings_data[:null_index].decode("utf-8")

        return ParameterStatus(
            header=header,
            name=param_name,
            value=param_value,
        )


@dataclass
class ReadyForQuery:
    header: Header
    status: str

    @staticmethod
    def from_bytes(raw: bytes, header: Header) -> "ReadyForQuery":
        *_, status = struct.unpack("!cIc", raw)
        return ReadyForQuery(header=header, status=status.decode())


@dataclass
class CopyBothResponse:
    header: Header
    copy_format: int
    num_columns: int
    column_formats: list[int]

    @staticmethod
    def from_bytes(raw: bytes, header: Header) -> "CopyBothResponse":
        return CopyBothResponse(
            header=header,
            copy_format=1,
            num_columns=0,
            column_formats=[],
        )


@dataclass
class CopyData:
    header: Header
    data: bytes

    @staticmethod
    def from_bytes(raw: bytes, header: Header) -> "CopyData":
        return CopyData(header=header, data=raw[5:])


def sequence_split_at(seq: bytes, idx: int) -> tuple[bytes, bytes]:
    left = seq[:idx]
    right = seq[idx:]
    return left, right


def parse(sequence: bytes) -> Generator:
    while sequence:
        header = Header.from_bytes(sequence)
        to_parse, sequence = sequence_split_at(sequence, header.length + 1)

        print(header)

        match header.type:
            case "R":
                yield AuthenticationOk.from_bytes(to_parse, header)
            case "S":
                yield ParameterStatus.from_bytes(to_parse, header)
            case "K":
                yield BackendKeyData.from_bytes(to_parse, header)
            case "Z":
                yield ReadyForQuery.from_bytes(to_parse, header)
            case "W":
                yield CopyBothResponse.from_bytes(to_parse, header)
            case "d":
                yield CopyData.from_bytes(to_parse, header)
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
    buffer = bytearray()
    while True:
        if recved := s.recv(2**20):
            print("---->", recved)
            for x in parse(recved):
                if isinstance(x, CopyData):
                    print(x)

                    print("-" * 100)


def main() -> None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            connect(s)
    finally:
        s.close()


if __name__ == "__main__":
    main()
