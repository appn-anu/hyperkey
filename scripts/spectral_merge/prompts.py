from __future__ import annotations


def select_from_list(items: list[str], prompt_label: str) -> str:
    """Interactive menu for choosing a file/folder or entering one manually."""
    print(f"\n--- Select {prompt_label} ---")
    print("[0] ENTER MANUALLY / TYPE PATH")

    for index, item in enumerate(items, 1):
        print(f"[{index}] {item}")

    while True:
        choice = input(f"Enter number (0-{len(items)}): ").strip()

        if choice == "0":
            manual_value = input(f"Type the manual value for {prompt_label}: ").strip()
            if manual_value:
                return manual_value
            print("Input cannot be empty.")
            continue

        if choice.isdigit():
            selected_index = int(choice) - 1
            if 0 <= selected_index < len(items):
                return items[selected_index]

        print(f"Invalid selection. Please enter 0 or 1-{len(items)}.")
