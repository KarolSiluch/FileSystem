# Program symulujący system plików karty SD


## Description
A robust, fault-tolerant file system designed to maintain data integrity even in the event of unexpected interruptions during file operations.

### Features
- Atomic Operations: Every file operation is executed atomically, ensuring that the system is never left in an inconsistent or corrupted state.
- Interrupt Resilience: Built-in mechanisms to recover and complete or roll back operations after an unexpected interruption.

### Core File Operations:
- Initialize new files safely.
- Add data to existing files without risk of data loss.
- Retrieve file content reliably.
- Remove files while ensuring metadata consistency.
- Utilizes a dedicated, reserved memory segment at the beginning of the storage to track pending operations and recovery data.

## System Recovery
Upon initialization, the system checks the "operation flag" in the Control Block. If a previous operation was interrupted (flag is raised), the system automatically resumes the process—updating the allocation table and file descriptors as needed—before clearing the flag .

## Memory map
| Area Name | Size | Description|
| --------- |----- | -----------|
| Control Block | 8 Bytes | Stores data for the transactional mechanism |
| Descriptor Table | 128 Bytes | Stores file metadata |
| Block Map |	16 Bytes | Bit-based map for data block allocation |
| Data Area	| 3944 Bytes | Storage for actual file content |
