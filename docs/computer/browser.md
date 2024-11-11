# Browser Class Documentation

## Overview
The Browser class provides a high-level interface for controlling a web browser using Selenium WebDriver. It handles browser automation, screen capture, and mouse/keyboard interactions.

## Key Features
- Headless/GUI browser operation
- Screen capture and frame buffering
- Mouse and keyboard event handling
- Element interaction and navigation
- Viewport management

## Important Size Considerations
There are two different size measurements to be aware of:

### Viewport Size
The viewport size is the visible browser area (976x732 by default). This is what you'll use for:
- Mouse coordinates
- Element positioning
- Window dimensions

### Screenshot Size
The actual screenshot capture size is smaller than the viewport (952x596 by default) due to browser UI elements and internal rendering. This affects:
- Captured frame dimensions
- Image processing operations
- Screen analysis

## Core Methods

### Initialization
```python
browser = Browser(headless=True, window_size=(976, 732))  # Sets viewport size
browser.launch() # Returns bool indicating success
```

### Navigation
```python
browser.navigate(url) # Navigate to URL
browser.wait_until_loaded() # Wait for page load
```

### Mouse Control
```python
browser.move_mouse(x, y) # Move mouse to coordinates within viewport
browser.click_mouse(button='left') # Click mouse (left/right/middle)
```

### Keyboard Control
```python
browser.type_text(text) # Type text
browser.press_key(key) # Press key
browser.release_key(key) # Release key
```

### Element Interaction
```python
element = browser.find_element(selector, timeout=None)
browser.is_field_active(field_id) # Check if input field is active
```

### Screen Capture
```python
frame = browser.get_current_frame() # Get current browser frame as PIL Image (952x596)
viewport = browser.get_viewport_size() # Get viewport dimensions (976x732)
rect = browser.get_window_rect() # Get browser window dimensions
```

## Integration with Mouse and Screen
- The Browser class provides mouse position tracking that syncs with the Mouse class
- Screen captures are automatically synchronized with the Screen class
- Mouse movements and clicks are translated to browser-native actions
- Keyboard events are passed directly to the active browser element

## Size-Related Methods
```python
# Get viewport dimensions (976x732)
width, height = browser.get_viewport_size()

# Get screenshot dimensions (952x596)
frame = browser.get_current_frame()
width, height = frame.size

# Get window position and size
x, y, width, height = browser.get_window_rect()
```

## Error Handling
- All methods return boolean success indicators
- Errors are logged with detailed messages
- Automatic cleanup on failure
- Graceful degradation when features are unavailable

## Best Practices
1. Always check return values for operation success
2. Use wait_until_loaded() after navigation
3. Verify element presence before interaction
4. Clean up resources with browser.close()
5. Handle exceptions for browser automation failures
6. Be aware of the difference between viewport and screenshot sizes when working with coordinates or image processing
7. Use viewport size for mouse movements and element interactions
8. Use screenshot size when working with captured frames
