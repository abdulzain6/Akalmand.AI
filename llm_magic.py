import re
import os
from langchain.vectorstores import FAISS
from langchain.document_loaders import UnstructuredFileLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.chains import ConversationalRetrievalChain
from langchain.chat_models import ChatOpenAI
from prompts import QA_PROMPT
from langchain.document_loaders import PlaywrightURLLoader
from langchain.schema import Document
from typing import List
from playwright.async_api import async_playwright
from unstructured.partition.html import partition_html
from langchain.document_loaders import YoutubeLoader
from pytube.exceptions import PytubeError
from lxml.html import fromstring
from deepgram import Deepgram
from langchain.schema import Document
from config import DEEPGRAM_API_KEY
import requests
import mimetypes
import magic

class AsyncPlaywrightURLLoader(PlaywrightURLLoader):
    async def aload(self) -> List[Document]:
        """Load the specified URLs using Playwright and create Document instances.

        Returns:
            List[Document]: A list of Document instances with loaded content.
        """
        docs: List[Document] = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            for url in self.urls:
                try:
                    page = await browser.new_page()
                    await page.goto(url)

                    for selector in self.remove_selectors or []:
                        elements = await page.locator(selector).all()
                        for element in elements:
                            if await element.is_visible():
                                await element.evaluate("element => element.remove()")

                    page_source = await page.content()
                    elements = partition_html(text=page_source)
                    text = "\n\n".join([str(el) for el in elements])
                    metadata = {"source": url}
                    docs.append(Document(page_content=text, metadata=metadata))
                except Exception as e:
                    if self.continue_on_failure:
                        print(f"Error fetching or processing {url}, exception: {e}")
                    else:
                        raise e
            await browser.close()

        return docs

def get_file_type(file_path):
    file_type = magic.from_file(file_path, mime=True)
    return file_type.split('/')[0] if file_type else None

def get_filename_from_path(file_path):
    return os.path.basename(file_path)


def replace_specials_with_underscores(string: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", string)


def injest_file(filename: str, index_name: str) -> str:
    loader = UnstructuredFileLoader(filename)
    docs = loader.load()
    docs = CharacterTextSplitter(chunk_size=1500).split_documents(docs)
    faiss = FAISS.from_documents(
        docs,
        embedding=OpenAIEmbeddings(),
    )
    faiss.save_local("Datastore", index_name)
    return " ".join([doc.page_content for doc in docs])


def chat_collection(index_name: str, question: str, chat_history: list):
    faiss = FAISS.load_local(
        index_name=replace_specials_with_underscores(index_name),
        embeddings=OpenAIEmbeddings(),
        folder_path="Datastore",
    )
    chain = ConversationalRetrievalChain.from_llm(
        ChatOpenAI(temperature=0.4),
        faiss.as_retriever(),
        combine_docs_chain_kwargs={"prompt": QA_PROMPT},
        verbose=True,
    )
    return chain({"question": question, "chat_history": chat_history})


async def add_url_to_memory(url: str, index_name: str):
    loader = AsyncPlaywrightURLLoader(urls=[url], remove_selectors=["header", "footer"])
    page = await loader.aload()
    text_splitter = CharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=1000, chunk_overlap=0
    )
    page_docs = text_splitter.split_documents(page)
    faiss = FAISS.from_documents(
        page_docs,
        embedding=OpenAIEmbeddings(),
    )
    faiss.save_local("Datastore", index_name)
    return " ".join([doc.page_content for doc in page_docs])


def get_page_title(link: str) -> str:
    try:
        page = fromstring(requests.get(link, timeout=1).content)
        return page.xpath("//title")[0].text_content()
    except Exception as e:
        print(f"=> Error getting transcript {e}")
        return ""


def get_video_transcript(url: str, page_title) -> list[Document]:
    try:
        try:
            loader = YoutubeLoader.from_youtube_url(url, add_video_info=True)
            return loader.load_and_split()
        except PytubeError:
            loader = YoutubeLoader.from_youtube_url(url, add_video_info=False)
            docs = []
            for doc in loader.load_and_split():
                doc.metadata[
                    "source"
                ] = f"""(Youtube Video ID is "{doc.metadata.get('source')}")
(Page title is '{page_title})'"""
                docs.append(doc)
            return docs
    except Exception as e:
        print(f"=> Error getting transcript {e}")
        return []


def get_and_persist_youtube_transcript(index_name: str, youtube_link: str) -> str:
    if "youtu.be" in youtube_link:
        youtube_link = f"https://www.youtube.com/watch?v={youtube_link.split('/')[-1]}"
    print("=> Getting page title")
    page_title = get_page_title(youtube_link)
    print(f"=> Got page title {page_title}")
    print("=> Getting transcript")
    documents = get_video_transcript(youtube_link, page_title)
    faiss = FAISS.from_documents(
        documents,
        embedding=OpenAIEmbeddings(),
    )
    faiss.save_local("Datastore", index_name)
    return " ".join([doc.page_content for doc in documents])



def get_transcription(filename: str, source: str):
    dg_client = Deepgram(DEEPGRAM_API_KEY)
    with open(filename, "rb") as audio:
        source_b = {"buffer": audio, "mimetype": get_file_type(filename)}
        response = dg_client.transcription.sync_prerecorded(source_b, {"punctuate": True})
        return [Document(
            page_content=response["results"]["channels"][0]["alternatives"][0][
                "transcript"
            ],
            metadata={"source": source},
        )]


def add_video_to_memory(index_name: str, filename: str, source: str) -> str:
    docs = get_transcription(filename, source)
    docs = CharacterTextSplitter(chunk_size=1500).split_documents(docs)
    faiss = FAISS.from_documents(
        docs,
        embedding=OpenAIEmbeddings(),
    )
    faiss.save_local("Datastore", index_name)
    return " ".join([doc.page_content for doc in docs])


