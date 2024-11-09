# Browser Class Documentation

## Overview
The Browser class provides a high-level interface for controlling a web browser using Selenium WebDriver. It handles browser automation, screen capture, and mouse/keyboard interactions.

## Key Features
- Headless/GUI browser operation
- Screen capture and frame buffering
- Mouse and keyboard event handling
- Element interaction and navigation
- Viewport management

## Core Methods

### Initialization
```python
browser = Browser(headless=True, window_size=(800, 600))
browser.launch() # Returns bool indicating success
```


### Navigation
```python
browser.navigate(url) # Navigate to URL
browser.wait_until_loaded() # Wait for page load``
```


### Mouse Control


```python
browser.move_mouse(x, y) # Move mouse to coordinates
browser.click_mouse(button='left') # Click mouse (left/right/middle)
```


### Keyboard Control


```python
browser.type_text(text) # Type text
browser.press_key(key) # Press key
browser.release_key(key) # Release key
Apply
Copy
```

### Element Interaction

```python
element = browser.find_element(selector, timeout=None)
browser.is_field_active(field_id) # Check if input field is active
```




### Screen Capture
```python
frame = browser.get_current_frame() # Get current browser frame as PIL Image
rect = browser.get_window_rect() # Get browser window dimensions
```


## Integration with Mouse and Screen
- The Browser class provides mouse position tracking that syncs with the Mouse class
- Screen captures are automatically synchronized with the Screen class
- Mouse movements and clicks are translated to browser-native actions
- Keyboard events are passed directly to the active browser element

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
