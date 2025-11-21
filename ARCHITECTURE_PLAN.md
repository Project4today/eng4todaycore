# Architecture Plan: Amazon Polly Integration

This document outlines the architecture for integrating Amazon Polly text-to-speech functionality into the AI Chatbox API.

## 1. Core Objectives

-   **Voice to AI Responses**: Provide an audio URL for every AI-generated message so the frontend can play it back to the user.
-   **Persona-Specific Voices**: Allow each defined persona to have a unique voice.
-   **Efficient Caching**: Avoid re-generating audio for the same text to save costs and improve performance.
-   **High-Performance History Loading**: Ensure that loading a long conversation with many audio files is fast and does not overload the server.

## 2. System Architecture

The implementation will be based on a server-side, cache-first approach using Amazon S3 as the storage layer for generated audio files.

### 2.1. Key Components

-   **Amazon Polly**: The AWS service used to convert text into speech.
-   **Amazon S3**: Used as a durable, high-performance file store (cache) for the generated `.mp3` audio files.
-   **Hashing**: A `sha256` hash of the content and voice will serve as the unique key for each audio file, enabling efficient caching.

### 2.2. Database Schema Changes

1.  **`personas` table**:
    -   Add a new column: `voice_id VARCHAR(100) NULL`. This will store the Amazon Polly voice ID associated with the persona (e.g., 'Joanna', 'Matthew').

2.  **`chat_sessions` table**:
    -   No direct changes are needed, as the `persona_id` already links a session to a persona (and thus to a voice).

### 2.3. Pydantic Model Changes

1.  **`models/chat.py`**:
    -   The `ChatMessage` model will be updated to include a new field: `audio_url: Optional[str] = None`. This field will hold the final S3 URL for the audio file corresponding to the message content.

### 2.4. Configuration

1.  **`.env` file**: The following new variables will be required:
    -   `AWS_ACCESS_KEY_ID`
    -   `AWS_SECRET_ACCESS_KEY`
    -   `AWS_REGION`
    -   `S3_BUCKET_NAME`
    -   `DEFAULT_POLLY_VOICE_ID` (e.g., 'Joanna') - This will be the fallback voice if a persona does not have one specified.

2.  **`core/config.py`**: This file will be updated to load these new environment variables.

---

## 3. API Workflow & Logic

### 3.1. New Message Generation (`POST /api/chat/{session_id}/message`)

This is the "write-through" caching part of the workflow.

1.  The endpoint receives a user's message.
2.  The AI (Gemini) generates a text response.
3.  **Determine Voice**: The backend determines the correct `voice_id` to use with the following priority:
    a. Look up the `persona_id` for the current session.
    b. If a `persona_id` exists, fetch the corresponding persona from the `personas` table and get its `voice_id`.
    c. If the session has no persona or the persona has no `voice_id`, fall back to using the `DEFAULT_POLLY_VOICE_ID` from the configuration.
4.  **Generate Cache Key**: A unique filename is created by hashing the combination of the AI's text response and the chosen `voice_id`.
    -   `filename = sha256(ai_text + voice_id).hexdigest() + ".mp3"`
5.  **Check S3 Cache**: The backend checks if an object with this `filename` already exists in the S3 bucket.
6.  **Cache Hit**: If the file exists, its public S3 URL is retrieved.
7.  **Cache Miss**: If the file does **not** exist:
    a. The backend calls the Amazon Polly API with the text and `voice_id`.
    b. The returned audio stream is uploaded directly to the S3 bucket with the `filename`.
    c. The public URL of the newly uploaded file is retrieved.
8.  **Update History**: The new AI message object, now including both the `content` (text) and the `audio_url`, is appended to the conversation history.
9.  **Return Response**: The API returns the `ChatSessionResponse` containing the full, updated history, including the new message with its `audio_url`.

### 3.2. Loading Historical Chat (`GET /api/chat/{session_id}`)

This workflow is optimized to be fast and avoid unnecessary API calls.

1.  The endpoint fetches the `chat_session` from the database, including its `history` and `persona_id`.
2.  **Determine Session Voice**: The backend determines the session's `voice_id` using the same fallback logic as in the new message workflow.
3.  **Enrich History**: The backend iterates through every message object in the `history` array.
    -   For each message where `role == 'model'`:
        a. It calculates the expected filename: `filename = sha256(message.content + voice_id).hexdigest() + ".mp3"`.
        b. It **constructs the expected S3 URL directly** without checking if the file exists (e.g., `https://<bucket>.s3.amazonaws.com/<filename>`).
        c. It populates the `audio_url` field of the message object with this constructed URL.
4.  **Return Response**: The API returns the `ChatSessionResponse` with the entire history now enriched with audio URLs for every AI message. The frontend is responsible for handling any potential 404s if a URL is requested but the file doesn't exist for some reason.
