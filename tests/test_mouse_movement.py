from computer.computer import Computer
import time

def test_mouse_movement():
    computer = Computer()
    computer.run()
    time.sleep(10)  # Allow time for Computer to initialize
    # move mouse
    # click
    mouse = computer.mouse
    position = mouse.position

    print(f"Mouse position: {position}")
    mouse.move_to(100, 100)
    time.sleep(1)
    position = mouse.position
    print(f"Mouse position: {position}")
    mouse.click(button='left')

if __name__ == "__main__":
    test_mouse_movement()
