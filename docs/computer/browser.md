# Browser Controller Documentation

The `BrowserController` class provides a high-level interface for automated browser control using Selenium WebDriver with Microsoft Edge. It includes functionality for mouse movement, clicking, typing, scrolling, and taking screenshots.

## Initialization
```python
browser = BrowserController(window_width=800, window_height=600)
```


The constructor initializes an Edge WebDriver instance with specified window dimensions. It automatically adjusts for viewport differences and sets up action chains for mouse control.

## Core Methods

### Navigation
```python
browser.navigate(url)
```

Navigates to the specified URL and waits for the page to load.

### Mouse Control
```python
browser.move_mouse_to(x, y)
browser.click_at(x, y)
```

- `move_mouse_to`: Moves the virtual mouse cursor to specified coordinates
- `click_at`: Moves to coordinates and performs a click action

### Element Location
```python
x, y = browser.locate_element_by_text("Click me")
```
Finds an element by its link text and returns its center coordinates.

### Text Input
```python
browser.type_text("Hello World")
browser.press_key("ENTER")
browser.click_and_type(x, y, "Hello World")
```

- `type_text`: Types text at the current cursor position
- `press_key`: Simulates a keyboard key press
- `click_and_type`: Combines clicking and typing in one operation

### Scrolling
```python
browser.scroll_down(amount=300)
browser.scroll_up(amount=300)
browser.scroll_to_element("Element text")
```

- `scroll_down`: Scrolls the page down by specified pixels
- `scroll_up`: Scrolls the page up by specified pixels
- `scroll_to_element`: Scrolls until the specified element is visible

### Screenshot Management
```python
browser.take_screenshot("images/screenshot.png")
```

Takes a screenshot and enhances it with:
- Current viewport coordinates (red)
- Screenshot coordinates (blue)
- Coordinate system overlay
- Automatic resizing to 1008x1008 pixels

### Coordinate System
```python
viewport_x, viewport_y = browser.normalize_coordinates(screenshot_x, screenshot_y, from_screenshot=True)
screenshot_x, screenshot_y = browser.normalize_coordinates(viewport_x, viewport_y, from_screenshot=False)
```

Converts coordinates between screenshot space (1008x1008) and viewport space.

### Cleanup
```python
browser.close()
```

Properly closes the browser and WebDriver instance.

## Important Notes

1. The browser window is automatically adjusted to account for differences between window and viewport sizes.
2. Screenshots are automatically enhanced with coordinate overlays for debugging.
3. All mouse movements are tracked and validated against viewport boundaries.
4. Most actions include built-in delays to ensure proper page loading and action completion.
5. Coordinate systems are maintained in both viewport and screenshot spaces (1008x1008).

## Error Handling

Most methods include try-except blocks and will:
- Print error messages when operations fail
- Continue execution when possible
- Provide meaningful feedback for debugging

## Dependencies

- Selenium WebDriver
- PIL (Python Imaging Library)
- Microsoft Edge WebDriver