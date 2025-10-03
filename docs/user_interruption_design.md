# User Interruption Design Document

## Overview

This document outlines the design for implementing user interruption (Ctrl+C) during long-running operations in the todo agent, specifically during LLM API calls and between tool executions.

## Requirements

### Functional Requirements
1. **Interruption Scope**: Allow user to interrupt during:
   - LLM API calls (primary use case)
   - Between tool executions (to avoid corruption)
2. **User Experience**: When interrupted, show "I stopped." message in standard assistant panel
3. **Conversation Continuity**: Preserve all conversation data up to and including the interrupted operation
4. **Simple Implementation**: Keep focused on user-initiated cancellation only

### Non-Functional Requirements
1. **Simplicity**: Minimal architectural changes
2. **Reliability**: No corruption of conversation state or tool execution
3. **Consistency**: Interruption works the same across all LLM providers

## Current Architecture

```
CLI.run() → CLI.handle_request() → Inference.process_request() → LLMClient._make_http_request()
```

**Key Components:**
- `CLI`: Main interaction loop, handles user input
- `Inference`: Orchestrates LLM requests and tool execution
- `LLMClient`: Makes HTTP requests to LLM APIs
- `ConversationManager`: Manages conversation history

## Design Approach

### Signal-Based Interruption

**Core Strategy**: Use Python's `signal` module to handle SIGINT (Ctrl+C) and set a cancellation flag that's checked at safe interruption points.

### Interruption Points

1. **Before LLM API calls** (in `Inference.process_request()`)
2. **Between tool executions** (in tool orchestration loop)
3. **During HTTP requests** (in `LLMClient._make_http_request()`)

### Signal Handler Placement

**Location**: `Inference` class
**Rationale**: 
- Orchestrates entire request processing
- Has access to conversation manager
- Can handle both API calls and tool execution boundaries

## Implementation Details

### 1. Signal Handler Setup

```python
class Inference:
    def __init__(self, ...):
        self._cancelled = False
        signal.signal(signal.SIGINT, self._handle_interrupt)
    
    def _handle_interrupt(self, signum, frame):
        self._cancelled = True
        # Don't exit immediately - let current operation finish
```

### 2. Cancellation Checks

**In `Inference.process_request()`:**
```python
def process_request(self, ...):
    # Check before LLM call
    if self._cancelled:
        return self._handle_cancellation()
    
    # Make LLM request
    response = self.llm_client.chat_with_tools(...)
    
    # Check after LLM call
    if self._cancelled:
        return self._handle_cancellation()
```

**In `LLMClient._make_http_request()`:**
```python
def _make_http_request(self, ...):
    # Check before request
    if self._cancelled:
        return self._create_cancelled_response()
    
    # Make HTTP request with short timeout
    response = requests.post(..., timeout=2)
    
    # Check after request
    if self._cancelled:
        return self._create_cancelled_response()
```

### 3. Cancellation Response

**Standard Response Format:**
```python
def _handle_cancellation(self):
    # Add "I stopped." to conversation
    self.conversation_manager.add_message(MessageRole.ASSISTANT, "I stopped.")
    
    # Reset cancellation flag
    self._cancelled = False
    
    # Return formatted response
    return "I stopped.", 0.0  # (message, thinking_time)
```

### 4. HTTP Request Cancellation

**Strategy**: Use short timeouts (1-2 seconds) and poll cancellation flag
```python
def _make_http_request(self, ...):
    start_time = time.time()
    timeout = 2  # Short timeout for responsiveness
    
    while time.time() - start_time < timeout:
        if self._cancelled:
            return self._create_cancelled_response()
        
        # Make request with very short timeout
        try:
            response = requests.post(..., timeout=1)
            return self._process_response(response)
        except requests.exceptions.Timeout:
            continue  # Check cancellation flag and retry
    
    # If we get here, we've hit the overall timeout
    return self._create_timeout_response()
```

## State Management

### Cancellation Flag
- **Scope**: Instance variable in `Inference` class
- **Reset**: Automatically reset after each interruption
- **Thread Safety**: Not needed (single-threaded application)

### Conversation State
- **Preservation**: All conversation data up to interruption point is preserved
- **Addition**: "I stopped." message added as normal assistant message
- **Continuity**: Conversation continues normally after interruption

## Error Handling

### User Interruption Only
- **Scope**: Only handle SIGINT (Ctrl+C)
- **Exclusions**: Don't handle system timeouts, network errors, or other exceptions
- **Rationale**: Keep implementation simple and focused

### Graceful Degradation
- **Partial Responses**: Any partial assistant responses are preserved
- **Tool Execution**: Interrupt only between tool executions, not during
- **State Consistency**: Ensure conversation state remains consistent

## Testing Strategy

### Unit Tests
1. **Signal Handler**: Test signal handler sets cancellation flag
2. **Cancellation Checks**: Test cancellation checks at each interruption point
3. **Response Format**: Test "I stopped." message format

### Integration Tests
1. **End-to-End**: Test full interruption flow from CLI to response
2. **Provider Agnostic**: Test with both OpenRouter and Ollama clients
3. **Conversation Continuity**: Test conversation state after interruption

### Manual Testing
1. **Timing**: Test interruption during various phases of LLM processing
2. **User Experience**: Verify "I stopped." appears in standard assistant panel
3. **Recovery**: Test that subsequent requests work normally after interruption

## Implementation Plan

### Phase 1: Core Signal Handling
**Objective**: Implement basic signal handling and cancellation infrastructure
**Acceptance Criteria**: AC1, AC2 (partial), AC5 (partial), AC6 (partial)

#### Task List:
1. **Add signal handling imports and setup**
   - [ ] Import `signal` module in `inference.py`
   - [ ] Add `_cancelled` instance variable to `Inference.__init__()`
   - [ ] Create `_handle_interrupt()` method to set cancellation flag
   - [ ] Register signal handler in `Inference.__init__()` using `signal.signal(signal.SIGINT, self._handle_interrupt)`

2. **Implement cancellation response handling**
   - [ ] Create `_handle_cancellation()` method in `Inference` class
   - [ ] Add "I stopped." message to conversation using `conversation_manager.add_message(MessageRole.ASSISTANT, "I stopped.")`
   - [ ] Reset `_cancelled` flag to `False` after handling
   - [ ] Return formatted response tuple `("I stopped.", 0.0)`

3. **Add cancellation checks in process_request()**
   - [ ] Add cancellation check before LLM API call (line ~192 in current code)
   - [ ] Add cancellation check after LLM response received (line ~194 in current code)
   - [ ] Return cancellation response if `_cancelled` is True at either check point

4. **Create basic tests for signal handling**
   - [ ] Test `_cancelled` flag is set when signal handler is called
   - [ ] Test `_handle_cancellation()` method works correctly
   - [ ] Test cancellation checks in `process_request()` method

**Dependencies**: None (foundational phase)
**Estimated Effort**: 2-3 hours
**Success Criteria**: User can press Ctrl+C and see "I stopped." message, conversation state preserved

### Phase 2: HTTP Request Cancellation
**Objective**: Implement responsive HTTP request cancellation with polling
**Acceptance Criteria**: AC3, AC8 (partial), AC9 (partial)

#### Task List:
1. **Modify LLMClient base class for cancellation support**
   - [ ] Add `_cancelled` parameter to `_make_http_request()` method signature
   - [ ] Add cancellation check before making HTTP request
   - [ ] Implement short timeout polling strategy (1-2 second intervals)
   - [ ] Add cancellation check in polling loop
   - [ ] Create `_create_cancelled_response()` method for consistent cancelled responses

2. **Update HTTP request polling implementation**
   - [ ] Replace single `requests.post()` call with polling loop
   - [ ] Use very short timeouts (1 second) for individual requests
   - [ ] Check cancellation flag between polling attempts
   - [ ] Handle timeout exceptions gracefully in polling loop
   - [ ] Implement overall timeout (2 seconds) to prevent infinite polling

3. **Update concrete LLM client implementations**
   - [ ] Modify `OllamaClient.chat_with_tools()` to pass cancellation flag
   - [ ] Modify `OpenRouterClient.chat_with_tools()` to pass cancellation flag
   - [ ] Ensure both clients use the updated `_make_http_request()` method
   - [ ] Test provider-specific response handling with cancellation

4. **Update Inference class to pass cancellation flag**
   - [ ] Modify `process_request()` to pass `self._cancelled` to `llm_client.chat_with_tools()`
   - [ ] Ensure cancellation flag is accessible to LLM client
   - [ ] Test cancellation propagation from Inference to LLM client

5. **Create basic HTTP cancellation tests**
   - [ ] Test HTTP request cancellation works with both providers
   - [ ] Test that cancelled responses are properly formatted

**Dependencies**: Phase 1 (signal handling infrastructure)
**Estimated Effort**: 3-4 hours
**Success Criteria**: HTTP requests can be interrupted within 1-2 seconds, works with both providers

### Phase 3: Tool Execution Boundaries
**Objective**: Add cancellation checks between tool executions without corrupting active tools
**Acceptance Criteria**: AC4, AC6 (complete), AC7 (partial)

#### Task List:
1. **Analyze tool execution flow in Inference class**
   - [ ] Identify tool execution boundaries in `process_request()` method
   - [ ] Locate where tool calls are extracted and executed
   - [ ] Understand tool orchestration loop structure
   - [ ] Document safe interruption points between tool executions

2. **Add cancellation checks between tool executions**
   - [ ] Add cancellation check before each tool execution
   - [ ] Add cancellation check after each tool execution completes
   - [ ] Ensure no interruption during active tool execution
   - [ ] Preserve results of completed tools when interrupted

3. **Implement tool execution state preservation**
   - [ ] Ensure completed tool results are added to conversation
   - [ ] Maintain tool execution context during interruption
   - [ ] Handle partial tool execution scenarios gracefully
   - [ ] Test that tool execution state remains consistent

4. **Create basic tool execution cancellation tests**
   - [ ] Test cancellation between tool executions works
   - [ ] Test that completed tool results are preserved

**Dependencies**: Phase 1 (signal handling), Phase 2 (HTTP cancellation)
**Estimated Effort**: 2-3 hours
**Success Criteria**: Can interrupt between tool executions, no corruption of tool state

### Phase 4: Testing and Refinement
**Objective**: Comprehensive testing, performance validation, and user experience refinement
**Acceptance Criteria**: AC5 (complete), AC7 (complete), AC8 (complete), AC9 (complete), AC10

#### Task List:
1. **End-to-end testing**
   - [ ] Test basic interruption flow works end-to-end
   - [ ] Test interruption works with both LLM providers
   - [ ] Test that subsequent requests work after interruption

2. **User experience validation**
   - [ ] Test "I stopped." message appears correctly
   - [ ] Test conversation history is preserved
   - [ ] Test clean return to command prompt

3. **Final validation and cleanup**
   - [ ] Validate all acceptance criteria are met
   - [ ] Update code documentation
   - [ ] Final code review and cleanup

**Dependencies**: Phase 1, Phase 2, Phase 3 (all previous phases)
**Estimated Effort**: 2-3 hours
**Success Criteria**: All acceptance criteria met, system ready for production use

## Risks and Mitigations

### Risk: Signal Handler Conflicts
**Mitigation**: Use instance-based signal handler, not global

### Risk: HTTP Request Hanging
**Mitigation**: Use short timeouts and polling strategy

### Risk: Conversation State Corruption
**Mitigation**: Only interrupt at safe boundaries, preserve all state

### Risk: Performance Impact
**Mitigation**: Minimal overhead from cancellation checks

## Success Criteria

1. **Functional**: User can interrupt during LLM API calls with Ctrl+C
2. **User Experience**: "I stopped." message appears in standard assistant panel
3. **Reliability**: No conversation state corruption or tool execution corruption
4. **Simplicity**: Implementation remains focused and maintainable
5. **Compatibility**: Works with both OpenRouter and Ollama providers

## Acceptance Criteria

### AC1: Signal Handler Implementation
**Given** a running todo agent
**When** the user presses Ctrl+C during LLM API calls
**Then** the signal handler should:
- Set the cancellation flag to True
- Not immediately exit the process
- Allow current operation to complete gracefully

**Acceptance Tests:**
- [ ] Signal handler is registered in `Inference.__init__()`
- [ ] `_cancelled` flag is properly set when SIGINT is received
- [ ] Signal handler doesn't cause immediate process termination
- [ ] Multiple Ctrl+C presses don't cause issues

### AC2: LLM API Call Interruption
**Given** an active LLM API request
**When** the user presses Ctrl+C
**Then** the system should:
- Check cancellation flag before making the request
- Check cancellation flag after receiving the response
- Return "I stopped." message if cancelled
- Preserve all conversation data up to interruption point

**Acceptance Tests:**
- [ ] Cancellation check before `llm_client.chat_with_tools()` call
- [ ] Cancellation check after LLM response received
- [ ] "I stopped." message added to conversation history
- [ ] Conversation state remains consistent after interruption
- [ ] Works with both OpenRouter and Ollama providers

### AC3: HTTP Request Cancellation
**Given** an ongoing HTTP request to LLM API
**When** the user presses Ctrl+C
**Then** the HTTP client should:
- Use short timeouts (1-2 seconds) for responsiveness
- Poll cancellation flag during request
- Return cancelled response if interrupted
- Handle timeout exceptions gracefully

**Acceptance Tests:**
- [ ] HTTP requests use configurable short timeout (default 2 seconds)
- [ ] Cancellation flag is checked during request polling
- [ ] Timeout exceptions are handled without crashing
- [ ] Cancelled responses are properly formatted
- [ ] No hanging HTTP requests after interruption

### AC4: Tool Execution Boundaries
**Given** a multi-tool execution scenario
**When** the user presses Ctrl+C between tool executions
**Then** the system should:
- Check cancellation flag between tool calls
- Not interrupt during active tool execution
- Preserve results of completed tools
- Return "I stopped." message if cancelled

**Acceptance Tests:**
- [ ] Cancellation check between tool executions
- [ ] No interruption during active tool execution
- [ ] Completed tool results are preserved
- [ ] Tool execution state remains consistent
- [ ] Complex tool orchestration scenarios work correctly

### AC5: User Experience
**Given** any interruption scenario
**When** the user presses Ctrl+C
**Then** the user should see:
- "I stopped." message in the standard assistant panel
- No error messages or stack traces
- Clean return to command prompt
- Ability to continue conversation normally

**Acceptance Tests:**
- [ ] "I stopped." message appears in assistant panel
- [ ] No error messages or exceptions shown to user
- [ ] Clean return to command prompt after interruption
- [ ] Subsequent requests work normally after interruption
- [ ] Conversation history is preserved and accessible

### AC6: State Management
**Given** any interruption scenario
**When** the interruption is handled
**Then** the system should:
- Reset cancellation flag after handling
- Preserve all conversation data
- Maintain consistent internal state
- Allow normal operation to resume

**Acceptance Tests:**
- [ ] Cancellation flag is reset after each interruption
- [ ] Conversation manager state is preserved
- [ ] No memory leaks or state corruption
- [ ] System can handle multiple interruptions in sequence
- [ ] All internal components remain in consistent state

### AC7: Error Handling
**Given** various error scenarios
**When** interruption occurs
**Then** the system should:
- Handle only user-initiated interruptions (SIGINT)
- Not interfere with other exception handling
- Maintain graceful degradation
- Preserve error context when appropriate

**Acceptance Tests:**
- [ ] Only SIGINT signals trigger interruption handling
- [ ] Other exceptions (network, timeout, etc.) are handled normally
- [ ] Interruption doesn't mask other error conditions
- [ ] System remains stable after interruption during error conditions

### AC8: Performance Impact
**Given** normal operation
**When** interruption handling is active
**Then** the system should:
- Have minimal performance overhead
- Not impact normal operation speed
- Use efficient cancellation checking
- Maintain responsive user experience

**Acceptance Tests:**
- [ ] Cancellation checks add <1ms overhead per operation
- [ ] Normal operation performance is not degraded
- [ ] HTTP request timeouts are reasonable (1-2 seconds)
- [ ] Memory usage remains stable during operation

### AC9: Provider Compatibility
**Given** different LLM providers
**When** interruption occurs
**Then** the system should:
- Work identically across all providers
- Handle provider-specific response formats
- Maintain consistent behavior
- Support both OpenRouter and Ollama

**Acceptance Tests:**
- [ ] Interruption works with OpenRouter provider
- [ ] Interruption works with Ollama provider
- [ ] Response formatting is consistent across providers
- [ ] Provider-specific features are preserved during interruption

### AC10: Integration Testing
**Given** the complete system
**When** end-to-end interruption scenarios are tested
**Then** the system should:
- Handle all interruption points correctly
- Maintain conversation continuity
- Provide consistent user experience
- Pass all integration test scenarios

**Acceptance Tests:**
- [ ] End-to-end interruption flow works correctly
- [ ] Complex conversation scenarios handle interruption properly
- [ ] Tool execution scenarios work with interruption
- [ ] Long-running operations can be interrupted cleanly
- [ ] System recovers properly after interruption

## Future Considerations

### Potential Enhancements (Not in Scope)
- Configurable interruption behavior
- Interruption during tool execution (with proper cleanup)
- Async/await implementation for better responsiveness
- Progress indicators during long operations

### Maintenance Notes
- Signal handlers are process-specific
- Cancellation logic is centralized in `Inference` class
- HTTP request cancellation is provider-agnostic
