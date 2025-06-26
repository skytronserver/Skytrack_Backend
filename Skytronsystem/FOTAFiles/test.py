def compute_simple_checksum2(filename):
    """
    Computes a simple checksum by summing all bytes in the specified file
    and taking the result modulo 256.

    Parameters:
        filename (str): The path to the file for which the checksum is to be calculated.

    Returns:
        int: The checksum value as an integer (0-255). Returns 0xFF if an error occurs.
    """
    BUFFER_SIZE = 512  # Define the buffer size similar to the C implementation
    checksum = 0        # Initialize checksum accumulator

    try:
        # Open the file in binary read mode
        with open(filename, 'rb') as file:
            while True:
                # Read a chunk of data from the file
                data = file.read(BUFFER_SIZE)
                
                # If no more data is read, break the loop
                if not data:
                    break

                # Iterate over each byte in the chunk and add its value to the checksum
                for byte in data:
                    checksum += byte

        # Compute checksum modulo 256 to keep it within uint8_t range
        checksum &= 0xFF

        return checksum

    except FileNotFoundError:
        # Handle the case where the file does not exist
        print("\nFailed to open file for checksum calculation\n")
        return 0xFF  # Indicate error with an invalid checksum value

    except IOError:
        # Handle other I/O errors (e.g., permission issues, read errors)
        print("\nError reading file for checksum\n")
        return 0xFF  # Indicate error with an invalid checksum value

    except Exception as e:
        # Handle any other unforeseen exceptions
        print(f"\nAn unexpected error occurred: {e}\n")
        return 0xFF  # Indicate error with an invalid checksum value


checksum=compute_simple_checksum2("V1.2.4.bin")
print(f"Checksum for  : 0x{checksum:02X}")