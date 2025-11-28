import clingo
import sys
import re
import subprocess
import os
import time
from datetime import datetime
from collections import defaultdict

# Dictionary to accumulate profile durations
profile_data = defaultdict(float)
# Dictionary to store start times per key
profile_start_times = {}

def start_profile(key):
    """Start profiling for a specific key."""
    profile_start_times[key] = time.time()

def record_profile(key):
    """Record elapsed time for a specific key."""
    if key in profile_start_times:
        elapsed = time.time() - profile_start_times[key]
        profile_data[key] += elapsed
        del profile_start_times[key]  # Optional: remove to prevent reuse
    else:
        print(f"Warning: No start time recorded for key '{key}'")    

def print_profile():
    print("\n⏱️  Performance Profile:")    
    total = profile_data.get("Entire program", 0.0)
    if total == 0:
        print("No profiling data recorded for 'Entire program'.")
        return
    for operation, duration in sorted(profile_data.items(), key=lambda x: -x[1]):
        print(f"{operation:<30}: {duration:.4f}s ({duration/total*100:.1f}%)")
    

def get_user_limits():
    """Ask user what kind of limit they want to set."""
    start_profile("User input")
    print("\nChoose the type of limit you want to set:")
    print("1. Limit by number of answer sets")
    print("2. Limit by time (seconds)")
    print("3. No limits (run to completion)")


    while True:
        choice = input("Enter your choice (1, 2, or 3): ").strip()
        if choice in ['1', '2', '3']:
            break
        print("Invalid choice. Please enter 1, 2, or 3.")
    record_profile("User input")

    if choice == '3':
        return None, None

    while True:
        try:
            if choice == '1':
                limit = int(input("Enter maximum number of answer sets to compute: "))
            else:
                limit = int(input("Enter maximum time in seconds: "))
            if limit > 0:
                return choice, limit
            print("Limit must be a positive integer.")
        except ValueError:
            print("Please enter a valid integer.")

def extract_show_atoms(content):
    start_profile("Extract show atoms")
    """Extract atoms from #show directives in the input file."""
    show_atoms = []  
    for line in content:
        if "#project" in line.strip() and not line.strip().startswith("%"):
            match = re.search(r'#project\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\([a-zA-Z0-9_,]+\))?)\.', line)            
            if match:
                show_atoms.append(match.group(1))
    record_profile("Extract show atoms")
    return show_atoms

def generate_constraints(filtered_ex_atoms, filtered_in_atoms,nv_ex_atoms,nv_in_atoms):
    """Generate constraints based on the answer set and show atoms."""
    constraints = []
    # Convert answer set symbols to string names
    for atom in filtered_in_atoms:
        constraints.append(f":- not {atom}.")
    for atom in filtered_ex_atoms:        
        constraints.append(f":- {atom}.")
    for atom in nv_in_atoms:
        constraints.append(f":- not {atom}.")
    return constraints

def create_modified_program(original_file, constraints):
    """Create a new program by removing #show directives and adding constraints."""
    with open(original_file, 'r') as f:
        content = f.readlines()
    filtered_content = [
        line for line in content
        if not (line.lstrip().startswith('#project'))
    ]
    # Add new constraints
    modified_content = ''.join(filtered_content) + '\n' + '\n'.join(constraints)
    temp_filename = "modified.lp"
    with open(temp_filename, 'w') as f:
        f.write(modified_content)
    return temp_filename


def execute_fasb(modified_file):
    """Execute the fasb command on the modified program."""
    fasb_command = ["fasb", modified_file, "0", "facet_count.fsb"]
    try:
        result = subprocess.run(fasb_command, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error executing fasb command: {e}")
        print(f"FASB stderr output: {e.stderr}")
        return None

def execute_fasb_with_activate(modified_file, nv_in_atoms,nv_ex_atoms):
    """Execute the fasb command on the modified program."""
    actvate_facet = " ".join(str(atom) for atom in nv_in_atoms)
    if len(nv_in_atoms) > 0:
        fasb_args = f"+ facets {actvate_facet}\n#?\n?\n"  # Activate facets, REPL-style input as a string
    else:
        fasb_args = f"#?\n?\n"  # Activate facets, REPL-style input as a string        
    #print(f"\nFASB Arguments:\n{fasb_args}")
    with open("facet_count_act.fsb", "w") as file:
        file.write(fasb_args)
    fasb_command = ["fasb", modified_file, "0", "facet_count_act.fsb"]
    try:
        result = subprocess.run(fasb_command, capture_output=True, text=True, check=True)
        #print("FASB execution output:")
        #print(result.stdout)
        record_profile("FASB execution")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error executing fasb command: {e}")
        print(f"FASB stderr output: {e.stderr}")
        return None
        
def print_facets(facets_list):
    if facets_list:
        print(f"\n Facets :")
    for fc_index, facet in enumerate(facets_list, start=1):
        print(f" {fc_index}: {facet} ")    


def execute_fasb_with_fcuef(modified_file, nv_in_atoms,nv_ex_atoms):
    start_profile("FASB execution")
    """Execute the fasb command on the modified program."""
    actvate_facet = " ".join(str(atom) for atom in nv_in_atoms)
    if len(nv_in_atoms) > 0:
        fasb_args = f"+ facets {actvate_facet}\n#??\n"  # Activate facets, REPL-style input as a string
    else:
        fasb_args = f"#??\n"  # Activate facets, REPL-style input as a string        
    #facet counts under each facet ->  #??
    #print(f"\nFASB Arguments:\n{fasb_args}")
    with open("facet_count_act.fsb", "w") as file:
        file.write(fasb_args)
    fasb_command = ["fasb", modified_file, "0", "facet_count_act.fsb"]
    try:
        result = subprocess.run(fasb_command, capture_output=True, text=True, check=True)
        record_profile("FASB execution")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error executing fasb command: {e}")
        print(f"FASB stderr output: {e.stderr}")
        record_profile("FASB execution")
        return None    


def facet_processing(filtered_ex_atoms, filtered_in_atoms, nv_ex_atoms, nv_in_atoms, projected_file):
    facets_count = 0
    facets_list = []
    
    start_profile("Generate constraints")
    constraints = generate_constraints(filtered_ex_atoms, filtered_in_atoms, nv_ex_atoms, nv_in_atoms)
    record_profile("Generate constraints")
    start_profile("Create modified program")
    modified_file = create_modified_program(projected_file, constraints)
    record_profile("Create modified program")
    start_profile("**FASB execution")
    stdout = execute_fasb(modified_file)
    record_profile("**FASB execution")

    if stdout is None:
        return []

    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    opt_lines = stdout.splitlines()

    # Remove empty lines
    r_emp_lines = [line for line in opt_lines if line.strip()]

    # Remove ANSI codes and filter out lines starting with "::"
    lines = [
        line for line in r_emp_lines
        if not ansi_escape.sub('', line).strip().startswith("::")
    ]
    try:
        facets_count = int(lines[1])
    except (IndexError, ValueError):
        print("Invalid or missing facet count format.")
        return []
    
    if facets_count == 0:
        return []

    if facets_count > 0 and len(lines) < 3:
        print("FASB output format unexpected.")
        return []

    facets_list = sorted(lines[2].split())
    if len(facets_list) != facets_count / 2:
        print(f"Warning: Expected {facets_count} exclusive facets, but found {len(facets_list)}.")
        return []

    return facets_list


def facet_activate(filtered_ex_atoms,filtered_in_atoms,nv_ex_atoms,nv_in_atoms,projected_file):
    facets_count=0
    facets_list=[]
    print("\nFacet Count Processing:")
    fc_in_atoms=[]
    fc_ex_atoms=[]
    start_profile("Generate constraints")
    constraints = generate_constraints(filtered_ex_atoms, filtered_in_atoms,fc_ex_atoms,fc_in_atoms)
    record_profile("Generate constraints")
    start_profile("Create modified program")
    modified_file = create_modified_program(projected_file, constraints)
    record_profile("Create modified program")
    start_profile("FASB execution for activated atoms")
    stdout=execute_fasb_with_activate(modified_file, nv_in_atoms,nv_ex_atoms)
    record_profile("FASB execution for activated atoms")

    if stdout is None:
        return []
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')    
    opt_lines = stdout.splitlines()
    # Remove ANSI codes and filter lines
    lines = [
        line for line in opt_lines
        if not ansi_escape.sub('', line).strip().startswith("::")
    ]        
    try:
        facets_count = int(lines[2])
    except ValueError:
        print("Invalid facet count format.")
        return []
    if facets_count == 0:
        # print("No facets available.")        
        return []
    if facets_count > 0 and len(lines) < 3:
        print("FASB output format unexpected.")
        return []
    facets_list = sorted(lines[3].split())
    if len(facets_list) != facets_count/2:
        print(f"Warning: Expected {facets_count} exclusive facets, but found {len(facets_list)}.")
        return []
    return facets_list  

def facet_nav_call(filtered_ex_atoms,filtered_in_atoms,nv_ex_atoms,nv_in_atoms,projected_file):
    facet_list=facet_activate(filtered_ex_atoms,filtered_in_atoms,nv_ex_atoms,nv_in_atoms,projected_file) 
    print(f"\n✅Navigation path {nv_in_atoms}:")  
    print("Included Projected Atoms: ", filtered_in_atoms)
    print("Excluded Projected Atoms: ", filtered_ex_atoms)
    print("Facet Count: ",len(facet_list))
    #print_facets(facet_list)
    return facet_list

def facet_count_under_each(filtered_ex_atoms,filtered_in_atoms,nv_ex_atoms,nv_in_atoms,projected_file):
    # This function will count the number of elements under each facet
    fc_in_atoms=[]
    fc_ex_atoms=[]
    constraints = generate_constraints(filtered_ex_atoms, filtered_in_atoms,fc_ex_atoms,fc_in_atoms)
    modified_file = create_modified_program(projected_file, constraints)
    stdout=execute_fasb_with_fcuef(modified_file, nv_in_atoms,nv_ex_atoms)
    print(stdout)
    
    if stdout is None:
        return []

    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    opt_lines = stdout.splitlines()

    # Remove empty lines
    r_emp_lines = [line for line in opt_lines if line.strip()]

    # Remove ANSI codes and filter out lines starting with "::"
    lines = [
        line for line in r_emp_lines
        if not ansi_escape.sub('', line).strip().startswith("::")
    ]

    try:
        facets_count = int(lines[1])
    except (IndexError, ValueError):
        print("Invalid or missing facet count format.")
        return []

    if facets_count == 0:
        return []

    if facets_count > 0 and len(lines) < 3:
        print("FASB output format unexpected.")
        return []

    facets_list = sorted(lines[2].split())
    if len(facets_list) != facets_count / 2:
        print(f"Warning: Expected {facets_count} exclusive facets, but found {len(facets_list)}.")
        return []

def facet_navigation(facet_list,filtered_in_atoms,filtered_ex_atoms,projected_file):
    if len(facet_list) == 0:
        print("No facets available for navigation.")
        return
    nv_in_atoms = []
    nv_ex_atoms = []
    cnt=0
    while True:  
        cnt+=1   
        print("Bag of loop navigation atom",nv_in_atoms)
        print(f"\nNavigation round: {cnt}")
        start_profile("User input")
        command = input(f"\n 1: Deactivate previous facet \n 2: Deactivate all facets \n 3: Activate new facet \n 4: Diversity measure under each facet \n 5: Quit navigation \n Enter command (1/2/3/4/5): ").strip().lower()
        record_profile("User input")
        if command == '1':
            if len(nv_in_atoms) > 0:
                nv_in_atoms = nv_in_atoms[:-1]  # Remove last activated facet
                print("After pop navigation atom",nv_in_atoms)
                facet_list=facet_nav_call(filtered_ex_atoms,filtered_in_atoms,nv_ex_atoms,nv_in_atoms,projected_file)
            else:
                print("No previously activated facets to deactivate.")
                continue    
        if command == '2':            
            nv_in_atoms = []
            nv_ex_atoms = []
            facet_list=facet_nav_call(filtered_ex_atoms,filtered_in_atoms,nv_ex_atoms,nv_in_atoms,projected_file)
        if command == '3':
            print(f"\nSelect from available facets:\n") 
            for fc_index, facet in enumerate(facet_list):
                print(f"{fc_index + 1}: {facet}")
            start_profile("User input")
            print(f"\nSelect checking whether every element in command_indices is within the valid range of indices for facet_list. list of facets by their indices separated by commas (e.g., 1,3,5):")
            command = input(f"\nRange available for Navigation [1, ..., {len(facet_list)}]: ")
            record_profile("User input")
            try:
                command_indices = [int(i) for i in command.split(",")]
                # validate indices
                # checking whether every element in command_indices is within the valid range of indices for facet_list.
                if all(1 <= i <= len(facet_list) for i in command_indices):
                    #activate selected facets
                    facets = [facet_list[i - 1] for i in command_indices]
                    for facet in facets:
                        if facet in nv_in_atoms or facet in nv_ex_atoms:
                            print(f"Facet {facet} already included in navigation atoms.")
                            continue
                        else:
                            nv_in_atoms.append(facet)  
                    facet_list=facet_nav_call(filtered_ex_atoms,filtered_in_atoms,nv_ex_atoms,nv_in_atoms,projected_file)
                    continue
                else:
                    print("Invalid index. Please select correct indices.")
                    continue
            except ValueError:
                print("Invalid input. Please enter a numeric index.")    
                continue
        if command == '4':
            print("**** Outputting from command =4")
            facet_count_under_each(filtered_ex_atoms,filtered_in_atoms,nv_ex_atoms,nv_in_atoms,projected_file)
            continue
        if command == '5':
            print("Exiting navigation mode.")
            break


def answer_set_navigation(all_ans_sets,
                          all_ans_facets,
                          all_filtered_in_atoms,
                          all_filtered_ex_atoms,
                          projected_file):
    if len(all_ans_sets) == 0:
        print("No answer set available for navigation.")
        return
    ans_index = 0
    print(f"\nAvailable Answer Set Options:\n")
    for ans_index, ans_set in enumerate(all_ans_sets):
        print(f"{ans_index + 1}: {ans_set}")
    start_profile("User input")
    command = input(f"\nSelect Answer Set Index for Navigation [1, ..., {len(all_ans_sets)}]: ")
    record_profile("User input")
    try:
        command_index = int(command)
        if 1 <= command_index <= len(all_ans_sets):
            selected_index = command_index - 1
            facet_navigation(all_ans_facets[selected_index],
                    all_filtered_in_atoms[selected_index],
                    all_filtered_ex_atoms[selected_index],projected_file)
        else:
            print("Invalid index. Please select a valid answer set.")
    except ValueError:
        print("Invalid input. Please enter a numeric index.")


def main(projected_file, limit_type=None, limit_value=None):
    print("Main started:",datetime.now())
    navigation_flag=False
    start_profile("User input")
    nav_input = input("Do you want to enable navigation mode? (y/n): ").strip().lower()
    if nav_input == 'y':
        navigation_flag = True
    record_profile("User input")            

    with open(projected_file, 'r') as f:
        content = f.readlines()
            
    #--- Extract show atoms
    show_atoms = extract_show_atoms(content)
    if not show_atoms:
        print("Error: No projection in input ASP. Program bypassed.")
        return
    else:
        print(f"\nProjected atoms extracted: {show_atoms}\n\n")

    # Initialize solver and counters
    start_profile("**Clingo time(Projection + Facet Count algorithm)")
    ctl = clingo.Control(["0", "--project"])
    ctl.load(projected_file)
    ctl.ground([("base", [])])
    ans_solve_start = time.time()
    all_ans_sets=[]
    all_ans_facets=[]
    all_filtered_in_atoms=[]
    all_filtered_ex_atoms=[]
    nv_in_atoms=[]
    nv_ex_atoms=[]
    ans_idx=0
    with ctl.solve(yield_=True) as handle:
        for model in handle:
            if limit_type =='1':
                if ans_idx >= limit_value:
                    print(f"\n🔢 Answer set limit of {limit_value} reached")
                    break
            if limit_type =='2':
                elapsed = time.time() - ans_solve_start
                print("checking limit type=",limit_type," and limit value=", limit_value)
                if elapsed >= limit_value:
                    print("checking elapsed=",elapsed)
                    print(f"\n⏰ Time limit of {limit_value} seconds reached")
                    break              
            answer_set = model.symbols(shown=True)
            if answer_set:    
                ans_idx= ans_idx + 1             
                answer_set_strs = set(map(str, answer_set))
                filtered_in_atoms = [atom for atom in show_atoms if atom in answer_set_strs]
                filtered_ex_atoms = [atom for atom in show_atoms if atom not in answer_set_strs]                  
                start_profile("****Facet Count algorithm")
                if filtered_in_atoms:
                    facet_list=facet_processing(filtered_ex_atoms,
                                                filtered_in_atoms,
                                                nv_ex_atoms,
                                                nv_in_atoms,
                                                projected_file)
                    print(f"\n✅Answer Set {ans_idx}: {answer_set}")        
                    print("\nAnswer Set with ONLY projected atom: [", (', '.join(filtered_in_atoms)),"]")
                    print("Facet Count: ",len(facet_list))
                    record_profile("****Facet Count algorithm")
                    if navigation_flag:            
                        all_ans_sets.append(answer_set)
                        all_filtered_in_atoms.append(filtered_in_atoms)
                        all_filtered_ex_atoms.append(filtered_ex_atoms)
                        all_ans_facets.append(facet_list)            
                else:
                    # Handle the case when no atoms match
                    print(f"No matching atoms present between projection set and answer set for:\n⚠️Answer Set {ans_idx}: {answer_set}")
            #start_profile("**Clingo time")        
        record_profile("Clingo time(Projection + Facet Count algorithm)")
    print(f"\nTotal answer sets found: {ans_idx}")


    # Start navigation if enabled
    if navigation_flag:
        print("\n Navigation Mode Activated")
        answer_set_navigation(all_ans_sets,
                              all_ans_facets,
                              all_filtered_in_atoms,
                              all_filtered_ex_atoms,
                              projected_file
                              )
                              
  



if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py [/path-to/instance.lp] /path-to/encoding.lp [/path-to/projection.lp]")
        sys.exit(1)

    projected_file = None # Initialize projected_file outside of the try block        
    try:    
        # Record program start time
        start_profile("Entire program") 

        # --- File Creation and Concatenation Logic ---
        input_file_1 = sys.argv[1] 
        # Create projected file with name projected_timestamp.lp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        projected_file = f"projected_{timestamp}.lp"
        
        # Concatenate all input files into projected file
        with open(projected_file, 'w') as outfile:
            with open(input_file_1, 'r') as infile1:
                outfile.write(infile1.read())
            if len(sys.argv) > 2:
                input_file_2 = sys.argv[2]
                with open(input_file_2, 'r') as infile2:
                    outfile.write(infile2.read())
            if len(sys.argv) > 3:
                input_file_3 = sys.argv[3]
                with open(input_file_3, 'r') as infile3:
                    outfile.write(infile3.read()) 

        # Get user preferences
        limit_type, limit_value = get_user_limits()
        # Run the main program with the specified limits
        main(projected_file, limit_type, limit_value)
        # Print detailed profile
        record_profile("Entire program")
        print_profile()

    except Exception as e:
        print(f"An error occurred in the main execution block: {e}")
        # Re-raise the exception after printing the error if you want the program to truly 'abort'
        raise         
    finally:
        # --- Cleanup Logic ---
        # This block runs whether the 'try' succeeds or fails
        if projected_file and os.path.exists(projected_file):
            #print(f"Cleanup: Deleting temporary file {projected_file}")
            os.remove(projected_file)        