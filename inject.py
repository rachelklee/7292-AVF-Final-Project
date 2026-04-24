import random
import subprocess
import os

os.makedirs("logs", exist_ok=True)
all_logs = []

NUM_INJECTS = 300

EXPECTED_OUTPUT = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
BIN_PATH = "/bin/ls"
LIST_DIR = "testdir"
LOG_FILE = f"logs/experiment_log.txt"

num_correct = 0
error_count = 0
sdc_count = 0
timeout_count = 0

open(LOG_FILE, "w").close()

for i in range(NUM_INJECTS):
    print ("======= Inject " + str(i) + " =======")
    output_file = "output/inject_" + str(i) + ".txt"

    # generate random values for inject
    # random number for step
    stepi_num = random.randint(1,509500)
    print("# of steps: " + str(stepi_num))

    # random number for register
    reg_num = random.randint(1,30)
    # print("register number: " + str(reg_num))

    reg_name = "x" + str(reg_num)
    print("register name for inject: " + reg_name)

    # random number for bit
    bit_num = random.randint(0,63)
    print("bit to inject: " + str(bit_num))

    # setup command for injects
    # reg value check
    reg_val_check = "p/x $" + reg_name
    # print(reg_val_check)

    # inject command
    # inject_command = f"set ${reg_name} = ${reg_name} ^ (1 << {bit_num})"
    inject_command = f"set ${reg_name} = ${reg_name} ^ ((unsigned long long)1 << {bit_num})"
    # print(inject_command)

    gdb_command_sequence = [
        "gdb",
        "-q",
        "-batch",
        "-ex", "set pagination off",
        "-ex", "set confirm off",
        "-ex", "set debuginfod enabled off",
        "-ex", f"set args -1 {LIST_DIR}",
        "-ex", "starti",
        "-ex", f"stepi {stepi_num}",
        "-ex", reg_val_check,
        "-ex", inject_command,
        "-ex", reg_val_check,
        "-ex", "continue",
        "-ex", "quit",
        BIN_PATH
    ]

    try:
        execution = subprocess.run(gdb_command_sequence, capture_output=True, text=True, errors="replace", timeout=60)

        execution_output = execution.stdout
        combined_output = execution.stdout + "\n" + execution.stderr

        # with open(LOG_FILE, "a") as f:
        #     f.write(f"\n===== INJECT {i} =====\n")
        #     f.write(f"steps={stepi_num}, reg={reg_name}, bit={bit_num}\n")
        #     f.write("\n----- STDOUT -----\n")
        #     f.write(execution.stdout)
        #     f.write("\n----- STDERR -----\n")
        #     f.write(execution.stderr)
        #     f.write("\n")

        inject_entry_log = []
        inject_entry_log.append(f"\n===== INJECT {i} =====\n")
        inject_entry_log.append(f"steps={stepi_num}, reg={reg_name}, bit={bit_num}\n")
        inject_entry_log.append("\n----- STDOUT -----\n")
        inject_entry_log.append(execution.stdout)
        inject_entry_log.append("\n----- STDERR -----\n")
        inject_entry_log.append(execution.stderr)
        inject_entry_log.append("\n")

        all_logs.append("".join(inject_entry_log))

        returned_output = []

        for line in execution_output.splitlines():
            stripped_line = line.strip()
            if stripped_line.isdigit():
                returned_output.append(stripped_line)

        error_strings = [
            "Segmentation fault",
            "Program received signal",
            "exited with code",
            "Inconsistency detected by ld.so",
            "Assertion",
            "not found",
            "Illegal instruction",
            "Aborted",
            "error while loading shared libraries",
            "cannot open shared object file",
            "failed to map segment",
            "cannot access memory",
        ]

        error_found = any(error_str in combined_output for error_str in error_strings)

        if error_found or len(returned_output) == 0:
            inject_result = "error"
            error_count += 1
        elif returned_output == EXPECTED_OUTPUT:
            inject_result = "no error"
            num_correct += 1
        elif not all(x.isdigit() for x in returned_output):
            inject_result = "error"
            error_count += 1
        elif sorted(returned_output) != sorted(EXPECTED_OUTPUT):
            inject_result = "sdc"
            sdc_count += 1
        else:
            inject_result = "sdc"
            sdc_count += 1

        print("inject result: " + inject_result + "\n")

    except subprocess.TimeoutExpired:
        print("inject result: timeout\n")
        timeout_count += 1
        
        timeout_log = []
        timeout_log.append(f"\n===== INJECT {i} =====\n")
        timeout_log.append(f"steps={stepi_num}, reg={reg_name}, bit={bit_num}\n")
        timeout_log.append("result=timeout\n")
        timeout_log.append("GDB timed out before completion.\n")
        all_logs.append("".join(timeout_log))

print("======= Test Summary =======")
print("...testing complete")
print("...this test ran " + str(NUM_INJECTS) + " injects\n")
print("Correct: " + str(num_correct))
print("Error: " + str(error_count))
print("SDC: " + str(sdc_count))
print("Timeout: " + str(timeout_count))

avf = (error_count + timeout_count + sdc_count) / NUM_INJECTS
sdc_avf = sdc_count / NUM_INJECTS

print("AVF: ", avf)
print("SDC AVF: ", sdc_avf)

print("=========== End ===========\n")

with open(LOG_FILE, "a") as f:
    f.write("".join(all_logs))

    f.write("======= Test Summary =======\n")
    f.write("...this test ran " + str(NUM_INJECTS) + " injects\n")
    f.write(f"Correct: { str(num_correct)}\n")
    f.write(f"Error: {str(error_count)}\n")
    f.write(f"SDC: {str(sdc_count)}\n")
    f.write(f"Timeout: {str(timeout_count)}\n")

    f.write(f"AVF: {avf}\n")
    f.write(f"SDC AVF: {sdc_avf}\n")
