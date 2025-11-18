# API Documentation: AI Chatbox v1.1

This document provides the necessary API details for the frontend team to implement the chat, chat history, and persona management features.

## High-Level Overview

The API is divided into two main parts:
1.  **Persona Management**: A full CRUD API to create, read, update, and delete AI personas.
2.  **Chat Interaction**: API endpoints to start chat sessions, send messages, and retrieve conversation history.

---

## 1. Persona Management API (`/api/personas`)

These endpoints allow for the management of the AI personalities available in the application.

### GET `/api/personas`
-   **Purpose**: Retrieves a list of all available personas.
-   **Success Response (200 OK)**: An array of `Persona` objects.
-   **Example `curl`**: `curl -X GET "http://localhost:8000/api/personas" -H "accept: application/json"`

### POST `/api/personas`
-   **Purpose**: Creates a new persona.
-   **Request Body**: A `Persona` object. `role_name`, `goal`, `personality`, and `setting` are required.
-   **Success Response (201 Created)**: The newly created `Persona` object, including its `prompt_id`.
-   **Example `curl`**:
    ```sh
    curl -X POST "http://localhost:8000/api/personas" \
         -H "accept: application/json" -H "Content-Type: application/json" \
         -d '{
               "role_name": "Test Persona",
               "goal": "To be a test.",
               "personality": "Curious and helpful.",
               "setting": "A virtual test environment."
             }'
    ```

### PUT `/api/personas/{prompt_id}`
-   **Purpose**: Updates an existing persona.
-   **Path Parameter**: `prompt_id` (integer) of the persona to update.
-   **Request Body**: A `Persona` object containing the fields to be updated.
-   **Success Response (200 OK)**: The complete, updated `Persona` object.
-   **Example `curl`**:
    ```sh
    curl -X PUT "http://localhost:8000/api/personas/1" \
         -H "accept: application/json" -H "Content-Type: application/json" \
         -d '{ "expertise": "Now includes advanced testing methodologies." }'
    ```

### DELETE `/api/personas/{prompt_id}`
-   **Purpose**: Deletes a persona.
-   **Path Parameter**: `prompt_id` (integer) of the persona to delete.
-   **Success Response (204 No Content)**: No body is returned on success.
-   **Example `curl`**: `curl -X DELETE "http://localhost:8000/api/personas/1" -H "accept: application/json"`

---

## 2. Chat Interaction API (`/api/chat`)

These endpoints manage the lifecycle of a user's conversation.

### POST `/api/chat/start`
-   **Purpose**: Creates a new, empty chat session. Can optionally set a default persona for the session.
-   **Request Body**:
    ```json
    {
      "user_id": 123,
      "system_prompt": "You are a friendly and encouraging English teacher."
    }
    ```
    - `user_id` (integer, optional): The ID of the user this session belongs to.
    - `system_prompt` (string, optional): The default persona/instruction for the AI for the entire session.
-   **Success Response (201 Created)**: A `StartChatSessionResponse` object.

### POST `/api/chat/{session_id}/message`
-   **Purpose**: Sends a message to a session and gets a response. Can optionally override the AI's persona, model version, and other settings for a single turn.
-   **Path Parameter**: `session_id` (UUID string).
-   **Request Body**:
    ```json
    {
      "message": "Please evaluate this paragraph about climate change.",
      "config": {
        "bot_version": "gemini-1.5-flash",
        "system_instruction": "You are an IELTS expert... Provide an estimated score.",
        "temperature": 0.5,
        "max_output_tokens": 800
      }
    }
    ```
    - `message` (string, required): The user's message.
    - `config` (object, optional): Overrides AI behavior for this specific request.
        - `bot_version` (string, optional): Specifies the AI model to use (e.g., "gemini-1.5-flash"). Defaults to the server's configured model if omitted.
        - `system_instruction` (string, optional): A temporary persona that overrides the session's default `system_prompt`.
        - `temperature`, `max_output_tokens`, etc. (optional): Other AI generation parameters.
-   **Success Response (200 OK)**: A `ChatSessionResponse` object containing the full, updated history and the `bot_version` that was used.

### GET `/api/chat/{session_id}`
-   **Purpose**: Retrieves the full message history for one specific chat session.
-   **Path Parameter**: `session_id` (UUID string).
-   **Success Response (200 OK)**: A `ChatSessionResponse` object.

### GET `/api/chat/users/{user_id}/sessions`
-   **Purpose**: Fetches a list of all non-empty chat sessions for a specific user, for displaying in a history sidebar.
-   **Path Parameter**: `user_id` (integer).
-   **Success Response (200 OK)**: An array of `UserSessionInfo` objects.
    ```json
    [
      {
        "session_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
        "updated_at": "2023-10-27T10:30:00Z",
        "title": "What is the capital of France?"
      }
    ]
    ```
    - `title`: The pre-generated name of the session, taken from the first user message.
