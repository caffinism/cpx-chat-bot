### Azure Language OpenAI Conversational Agent Accelerator: Responsible AI FAQ

- **What is `Azure-Language-OpenAI-Conversational-Agent-Accelerator`?**
    - The `Azure-Language-OpenAI-Conversational-Agent-Accelerator` project provides users with a code-first example on how to augment an existing RAG solution with Azure AI Language functionality. The system takes as input user chat messages (grounded within a specific context). The system orchestrates user chats to Azure AI Langauge CLU or CQA projects, or to a fallback RAG agent. Output is a system chat message, which may be the answer to a question in a CQA project, the result of a linked intent in a CLU project, or a general grounded response from RAG.

- **What can `Azure-Language-OpenAI-Conversational-Agent-Accelerator` do?**
    - Overall, the demo provided with this proejct showcases the following chat experience:
        - User inputs chat dialog.
        - AOAI node preprocesses by breaking input into separate utterances.
        - Orchestrator node routes each utterance to either CLU, CQA, or fallback RAG.
        - If CLU was called, call extended business logic based on intent/entities.
        - Agent summaries response (what business action was performed, provide answer to question, provide grounded response).

- **What is `Azure-Language-OpenAI-Conversational-Agent-Accelerator`'s intended uses?**
    - The `Azure-Language-OpenAI-Conversational-Agent-Accelerator` project is intended to display the "better together" story when using Azure AI Language and Azure OpenAI. This chat experience includes single-turn chatting, QA, and groundedness. When combined with an existing RAG solution, adding a `UnifiedConversationOrchestrator` object can help in the following ways:
        - manual overrides of DSAT examples using CQA.
        - extended chat functionality based on recognized intents/entities using CLU.
        - consistent fallback to original chat functionality with RAG.

- **How was `Azure-Language-OpenAI-Conversational-Agent-Accelerator` evaluated? What metrics are used to measure performance?**
    - `Azure-Language-OpenAI-Conversational-Agent-Accelerator` underwent red teaming RAI procedures to ensure metrics of harmful content and groundedness were met. 

- **What are the limitations of `Azure-Language-OpenAI-Conversational-Agent-Accelerator`? How can users minimize the impact of `Azure-Language-OpenAI-Conversational-Agent-Accelerator`'s limitations when using the system?**
    - System is not intended for use in the context of sensitive topics or harmful content. Ensure all system content is in the context of linked project data (e.g. Contoso Outdoors).

- **What operational factors and settings allow for effective and responsible use of `Azure-Language-OpenAI-Conversational-Agent-Accelerator`?**
    - Users provide their own AOAI resource. Depending on the AOAI model provided, accuracy of `Azure-Language-OpenAI-Conversational-Agent-Accelerator` may vary. If you choose to alter the provided example data, ensure that it meets guidelines of responsible AI practices.

- **How do I provide feedback on `Azure-Language-OpenAI-Conversational-Agent-Accelerator`?**
    - Please submit feedback through the GitHub repo by creating an issue. Issues will be triaged and addressed in a timely manner. You may also contact the team at <taincidents@microsoft.com>.