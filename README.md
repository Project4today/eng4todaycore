# API Documentation: AI Chatbox v0.1.0-beta

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

### GET `/api/personas/{prompt_id}`
-   **Purpose**: Retrieves a single, specific persona by its unique ID.
-   **Success Response (200 OK)**: A single `Persona` object.
-   **Example `curl`**: `curl -X GET "http://localhost:8000/api/personas/1" -H "accept: application/json"`

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
      "persona_id": 1
    }
    ```
    - `user_id` (integer, optional): The ID of the user this session belongs to.
    - `persona_id` (integer, optional): The ID of the default persona for the session.
-   **Success Response (201 Created)**: A `StartChatSessionResponse` object.

### POST `/api/chat/{session_id}/message`
-   **Purpose**: Sends a message to a session and gets a response. Can optionally override the AI's persona, model version, and other settings for a single turn.
-   **Path Parameter**: `session_id` (UUID string).
-   **Request Body**:
    ```json
    {
      "message": "Please evaluate this paragraph about climate change.",
      "persona_id": 2,
      "config": {
        "bot_version": "gemini-1.5-flash",
        "system_instruction": "You are an IELTS expert... Provide an estimated score.",
        "temperature": 0.5
      }
    }
    ```
    - `message` (string, required): The user's message.
    - `persona_id` (integer, optional): If provided, **changes the default persona** for this session for all future messages.
    - `config` (object, optional): Overrides AI behavior for this specific request.
        - `bot_version` (string, optional): Specifies the AI model to use (e.g., "gemini-1.5-flash").
        - `system_instruction` (string, optional): A temporary persona that overrides the session's default persona for this turn only.
-   **Success Response (200 OK)**: A `ChatSessionResponse` object containing the full, updated history.

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
