while True:
    print("--- C A L C U L E T T E R ---")
    print("\n" + '=' * 32)
    
    user_input = input("In:  ")
    
    total_value = 0
    for char in user_input.upper():
        if char.isalpha():
            total_value += ord(char) - 64
    
    print(f"Out: {total_value}\n")
    print("-"*32 + "\n")
