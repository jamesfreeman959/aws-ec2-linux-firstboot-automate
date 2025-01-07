import paramiko
import io
import time

def connect_serial_console(serial_console_endpoint, instance_id, private_key_pem, kernel_arguments):
    # Load the private key from memory (StringIO)
    private_key_file = io.StringIO(private_key_pem)
    private_key = paramiko.RSAKey.from_private_key(private_key_file)

    # Initialize the SSH client
    ssh = paramiko.SSHClient()

    # Load SSH host keys.
    ssh.load_system_host_keys()

    # Auto add host key policy (dangerous in production, but useful for testing)
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Connect to the instance serial console using SSH
    print(f"Connecting to {serial_console_endpoint} via SSH...")
    ssh.connect(serial_console_endpoint, username=instance_id + '.port0', pkey=private_key, allow_agent=False, look_for_keys=False)

    # Start an interactive shell session
    console = ssh.invoke_shell()

    # Send some keystrokes to interact with GRUB or the instance
    time.sleep(5)
    console.send('e')  # Example: 'e' to edit GRUB entry

    # Press the down arrow key 16 times - this works on the default Ubuntu config but will need changing for other OS and bootloaders
    for _ in range(16):
        # Send the down arrow key (ANSI escape sequence for down arrow is '\x1b[B')
        time.sleep(1)  # Add a slight delay to ensure shell is ready
        console.send('\x1b[B')  # This sends the down arrow key

    # Send the Ctrl+E key combination (ASCII control sequence for Ctrl+E is '\x05') to move the cursor to the line end
    time.sleep(1)  # Add a slight delay to ensure shell is ready
    console.send('\x05')  # This sends Ctrl+E

    time.sleep(1)
    console.send(' ' + kernel_arguments + '\n')  # Enter a space, the required kernel parameters, and enter

    time.sleep(1)
    console.send('\x18')  # Boot the modified kernel - send Ctrl+X

    # Read the output
    time.sleep(2)
    output = console.recv(10240).decode()
    print(output)

    # Close the connection
    ssh.close()