import struct
import math
import os
from dataclasses import dataclass

WORD_SIZE = 2
ALLOCATION_UNIT = 32

CONTROLL_BLOCK = 0
FILE_DESCRIPTOR_TABLE = 8
ALLOCATION_TABLE = 136
DATA = 152
END = 4088

FILE_DESCRIPTOR_SIZE = 8
WORDS_IN_ALLOCATION_UNIT = ALLOCATION_UNIT // WORD_SIZE

MAX_FILE_NUM = (ALLOCATION_TABLE - FILE_DESCRIPTOR_TABLE) // FILE_DESCRIPTOR_SIZE


@dataclass
class FileDescriptor:
    Status: int
    Size: int
    FirstBlock: int
    Name: str


@dataclass
class OpenFileDescriptor:
    DiskDescriptorIndex: int
    CursorPosition: int
    FirstBlock: int
    Size: int


class Disc:
    def __init__(self):
        self._disc = bytearray(4096)
        self.update_allocation_table(123, 5, 1)

    def write_string(self, start: int, text: str):
        data = text.encode('ascii')
        for i in range(0, len(data), 2):
            chunk = data[i:i + 2]
            if len(chunk) == 1:
                chunk += b'\x00'

            current_addr = start + i

            self.write_word(current_addr, struct.unpack('<H', chunk)[0])

    def write_word(self, start: int, content: int):
        if start % 2 != 0:
            raise ValueError(f"Invalid address: {start}.")

        if not (0 <= content <= 0xFFFF):
            raise ValueError(f"Invalid word: {content}.")

        self._disc[start:start + 2] = content.to_bytes(2, byteorder='little')

    def _read_raw_chunk(self, start: int) -> bytearray:
        if start % 2 != 0:
            raise ValueError(f"Invalid address: {start}.")
        return self._disc[start:start + 2]

    def read_number(self, start: int) -> int:
        chunk = self._read_raw_chunk(start)
        return int.from_bytes(chunk, byteorder='little', signed=False)

    def read_chars(self, start: int) -> str:
        chunk = self._read_raw_chunk(start)
        return chunk.decode('ascii').rstrip('\x00')

    def read_n_words(self, start: int, n: int):
        return [self.read_number(start + i * 2) for i in range(n)]

    def create_file(self, name: str, content: str):
        descriptor_index = 0
        file_descriptor = self.get_file_descriptor(descriptor_index)
        while file_descriptor.Status == 1:
            descriptor_index += 1
            file_descriptor = self.get_file_descriptor(descriptor_index)
            if descriptor_index >= MAX_FILE_NUM:
                raise MemoryError("Max number of files!")
        file_position = self.file_descriptor_addr(descriptor_index)

        start = self.find_allocation_table_chunk(math.ceil(len(content) / ALLOCATION_UNIT))
        self.write_string(start * ALLOCATION_UNIT + DATA, content)
        self.write_word(file_position, 1)
        self.write_word(file_position + 2, 0)
        self.write_word(file_position + 4, start)
        self.write_string(file_position + 6, name)
        self.save_transaction(descriptor_index, len(content))

    def save_transaction(self, file_id: int, new_size: int, error=False):
        self.write_word(CONTROLL_BLOCK + 2, file_id)
        self.write_word(CONTROLL_BLOCK + 4, new_size)
        self.write_word(CONTROLL_BLOCK, 1)
        if error:
            raise RuntimeError("Mock unplug")
        self.save_logic()

    def save_logic(self):
        descriptor_id = self.read_number(CONTROLL_BLOCK + 2)
        file_descriptor = self.get_file_descriptor(descriptor_id)
        file_position = self.file_descriptor_addr(descriptor_id)

        new_size = self.read_number(CONTROLL_BLOCK + 4)
        self.write_word(file_position + 2, new_size)
        unites_used = math.ceil(new_size / ALLOCATION_UNIT)

        start_block = file_descriptor.FirstBlock

        self.update_allocation_table(start_block, unites_used, 1)
        self.write_word(CONTROLL_BLOCK, 0)

    def read(self, open_file: OpenFileDescriptor) -> str:
        result = ''
        memoty_chunk = self.get_memoty_chunk(open_file.FirstBlock, open_file.CursorPosition)
        while open_file.CursorPosition < open_file.Size:
            local_cursor = open_file.CursorPosition % ALLOCATION_UNIT
            if local_cursor == 0 and open_file.CursorPosition // ALLOCATION_UNIT:
                memoty_chunk = self.get_memoty_chunk(open_file.FirstBlock, open_file.CursorPosition)
            result += memoty_chunk[local_cursor]
            open_file.CursorPosition += 1

        return result

    def delete(self, file: str) -> None:
        file_id, _ = self.get_file_by_name(file)
        self.delete_transaction(file_id)

    def delete_transaction(self, file_id: int):
        self.write_word(CONTROLL_BLOCK + 2, file_id)
        self.write_word(CONTROLL_BLOCK, 2)
        self.delete_logic()

    def delete_logic(self):
        descriptor_id = self.read_number(CONTROLL_BLOCK + 2)
        file_descriptor = self.get_file_descriptor(descriptor_id)
        file_position = self.file_descriptor_addr(descriptor_id)
        self.write_word(file_position, 2)

        delated_units = math.ceil(file_descriptor.Size / ALLOCATION_UNIT)
        self.update_allocation_table(file_descriptor.FirstBlock, delated_units, 0)
        self.write_word(CONTROLL_BLOCK, 0)

    def open(self, file: str) -> OpenFileDescriptor:
        file_id, file_desc = self.get_file_by_name(file)
        return OpenFileDescriptor(file_id, 0, file_desc.FirstBlock, file_desc.Size)

    def get_file_descriptor(self, id: int) -> FileDescriptor:
        file_address = id * FILE_DESCRIPTOR_SIZE + FILE_DESCRIPTOR_TABLE
        if file_address >= ALLOCATION_TABLE:
            raise IndexError("Index out of range!")
        return FileDescriptor(
            self.read_number(file_address),
            self.read_number(file_address + 2),
            self.read_number(file_address + 4),
            self.read_chars(file_address + 6)
        )

    def get_file_by_name(self, file: str) -> tuple[int, FileDescriptor]:
        for file_id in range(16):
            file_desc = self.get_file_descriptor(file_id)
            if file_desc.Status == 1 and file_desc.Name == file:
                return (file_id, file_desc)
        raise ValueError(f"File {file} does not exist")

    def find_allocation_table_chunk(self, size: int):
        streak = 0
        table = self.get_allocation_table()

        for i in range(len(table) * WORD_SIZE * 8):
            word_index = i // (WORD_SIZE * 8)
            bit_index = i % (WORD_SIZE * 8)
            current_word = table[word_index]
            occupied = (current_word >> bit_index) & 1
            if not occupied:
                streak += 1
                if streak == size:
                    return i - size + 1
            else:
                streak = 0
        raise MemoryError('Not enough memory!')

    def repair(self):
        operation = self.read_number(CONTROLL_BLOCK)
        if operation == 1:
            print("[SYSTEM] Dokańczanie zapisu danych.")
            self.save_logic()
        elif operation == 2:
            print("[SYSTEM] Dokańczanie usuwania pliku.")
            self.delete_logic()

    def extend_file(self, file: OpenFileDescriptor, content: str, error=False):
        if not self.can_fit(file, len(content)):
            raise MemoryError('Idk, by a new disc')

        start = DATA + file.FirstBlock * ALLOCATION_UNIT + file.Size
        new_size = file.Size + len(content)
        if file.Size % 2 == 1:
            start -= 1
            content = self.read_chars(start) + content
        self.write_string(start, content)
        self.save_transaction(file.DiskDescriptorIndex, new_size, error)
        file.Size = new_size

    def can_fit(self, file: OpenFileDescriptor, size: int) -> bool:
        table = self.get_allocation_table()

        extend_start = file.FirstBlock + math.ceil(file.Size / ALLOCATION_UNIT)
        new_units = math.ceil((file.Size + size) / ALLOCATION_UNIT) - math.ceil(file.Size / ALLOCATION_UNIT)
        for i in range(new_units):
            word_index = (i + extend_start) // (WORD_SIZE * 8)
            bit_index = (i + extend_start) % (WORD_SIZE * 8)
            current_word = table[word_index]
            if (current_word >> bit_index) & 1:
                return False
        return True

    def update_allocation_table(self, start: int, units: int, value: bool):
        table = self.get_allocation_table()

        for i in range(units):
            absolute_block_index = start + i
            word_index = absolute_block_index // (WORD_SIZE * 8)
            bit_index = absolute_block_index % (WORD_SIZE * 8)

            mask = 1 << bit_index
            if value:
                table[word_index] |= mask
            else:
                table[word_index] &= ~mask

        for id, word in enumerate(table):
            self.write_word(id * 2 + ALLOCATION_TABLE, word)

    def get_memoty_chunk(self, first_block: int, cursor: int):
        start = DATA + (first_block + cursor // ALLOCATION_UNIT) * ALLOCATION_UNIT
        memory_chunk = [self.read_chars(start + offset * 2) for offset in range(WORDS_IN_ALLOCATION_UNIT)]
        return ''.join(memory_chunk)

    def save_to_file(self, filename: str = "virtual_disk.bin"):
        try:
            with open(filename, 'wb') as f:
                f.write(self._disc)
            print(f"[SYSTEM] Pomyślnie zapisano stan dysku do pliku '{filename}'.")
        except IOError as e:
            print(f"[BŁĄD] Nie udało się zapisać pliku: {e}")

    def load_from_file(self, filename: str = "virtual_disk.bin"):
        if not os.path.exists(filename):
            print(f"[INFO] Plik '{filename}' nie istnieje. Pozostawiam czysty dysk.")
            return

        try:
            with open(filename, 'rb') as f:
                data = f.read()

            if len(data) != len(self._disc):
                raise ValueError(f"Rozmiar pliku ({len(data)} B nie zgadza się z rozmiarem dysku ({len(self._disc)} B!")

            self._disc = bytearray(data)
            self.repair()
            print(f"[SYSTEM] Pomyślnie załadowano stan dysku z '{filename}'.")

        except (IOError, ValueError) as e:
            print(f"[BŁĄD] Nie udało się wczytać dysku: {e}")

    def get_allocation_table(self):
        return [self.read_number(ALLOCATION_TABLE + i) for i in range(0, DATA - ALLOCATION_TABLE, 2)]

    @staticmethod
    def file_descriptor_addr(descriptor_id: int):
        return descriptor_id * FILE_DESCRIPTOR_SIZE + FILE_DESCRIPTOR_TABLE

    def getBytearray(self):
        return self._disc
