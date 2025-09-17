
import re

from prompts import RAG_BASE_PROMPT
from embeddings import load_document_collection
from chat_completion import run_completion

from loguru import logger
from pathlib import Path
from typing import Union, List


#load_dotenv()


def odata_escape(s: str) -> str:
    # OData string literals escape single quotes by doubling them
    return s.replace("'", "''")


class RAGError(Exception):
    pass

class RAGBackEnd:

    def __init__(self, user_id: str):
        logger.info(f"[User: {user_id}] Initialization of chatbot backend")
        # Load document collection
        self.document_collection = load_document_collection(user_id)
        self.document_filter = None


    
    def document_index_pipeline(self, files: Union[str, List[str]]):

        if isinstance(files, str):
            files = [files]

        uploaded_any = False

        for file_path in sorted(Path(p) for p in files):
            if not file_path.is_file():
                logger.warning(f"Skipped: {file_path} is not a valid file.")
                continue
            with open(file_path, "rb") as file_obj:
                uploaded = self.document_collection.add_file_to_blob_container(str(file_path), file_obj)
                if uploaded:
                    uploaded_any = True
        # now setup the client index pipeline and embed the documents:
        if uploaded_any:
            # At least one file was newly uploaded → (re)build the pipeline
            self.document_collection.setup_user_index_pipeline()
        else:
            logger.info("All files already existed; skipping user index pipeline setup.")
       

    def logout_delete_storage_pipeline(self):

        """
        Optional cleanup routine to be called during user logout.

        The purpose of this method is to reduce storage costs and remove temporary indexing 
        artifacts when persistent storage is no longer required. It deletes the following user-specific resources:

        - **Blob container**: Removes the user's dedicated container in blob storage.
        - **Vector index**: Deletes the index holding vector representations of the user's documents. 
        (This index is user-specific as it's tightly coupled with the user's container snapshot.)
        - **Indexer**: Removes the indexing pipeline defined for the user. 
        (Each indexer is bound to a specific index, hence user-scoped.)
        - **Skillset**: Deletes the Azure Cognitive Search skillset tied to the user’s indexing process.
        (Skillsets are also user-specific due to their dependency on the associated index.)
        - **Data source connection**: Cleans up the data source connection configured for the user.

        This operation is safe to perform at logout when persistence is not required and helps minimize unnecessary storage and indexing costs.
        """

        self.document_collection.user_logout_delete_pipeline()


    def get_document_filter(self, files: Union[str, List[str], None]):

        """
        Given a single file name or a list of file names, return an OData filter string
        to be used in chat completion filtering, using the 'title' field.

        Examples:
            get_document_filter("doc1.pdf")
            -> "title eq 'doc1.pdf'"

            get_document_filter(["doc1.pdf", "doc2.pdf"])
            -> "(title eq 'doc1.pdf' or title eq 'doc2.pdf')"
        """
        if not files:  # None or empty list
            return None

        if isinstance(files, str):
            files = [files]

        files = [f for f in files if f]  # drop falsy entries
        if not files:
            return None

        clauses = [f"title eq '{odata_escape(f)}'" for f in files]
        return clauses[0] if len(clauses) == 1 else f"({' or '.join(clauses)})"


    def query_rag(self, 
                  question: str = "", 
                  history: List[dict[str, str]] = None,
                  selected_files: List[str] = None,
                  response_format: str="text",
                  prompt_template: str = RAG_BASE_PROMPT
                  ):
        
        self.question = "\n" + question

        # Sanity check
        if self.document_collection is None:
            raise RAGError("No active document collection!")
        
        if "{selected_file}" in prompt_template:
            files_str = ", ".join(selected_files or [])
            prompt = prompt_template.format(selected_file=files_str)
        else:
            prompt = prompt_template
        

    # Get document filter
        self.document_filter = self.get_document_filter(selected_files)
        self.index_name = self.document_collection.index_name

        completion = run_completion(
            prompt=prompt + self.question,
            filter=self.document_filter, 
            index_name=self.index_name,
            response_format=response_format
        )

        text = completion.content or ""
        answer = re.sub(r'\[doc\d+\]', '', text)
        # tidy up any extra spaces like "met  ." or before punctuation
        answer = re.sub(r'\s{2,}', ' ', answer)
        answer = re.sub(r'\s+([,.;:!?])', r'\1', answer).strip()
        citations = completion.context.get('citations')

        return answer


    
        # Handle conversation history
        contextualized_question = "query : " + self.contextualize_question(question, history)



