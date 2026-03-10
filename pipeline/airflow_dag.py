from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
from agents.crawler_agent import CrawlerAgent
from agents.collector_agent import CollectorAgent
from agents.processing_agent import ProcessingAgent
from agents.embedding_agent import EmbeddingAgent

def crawl_task():
    crawler = CrawlerAgent()
    urls = crawler.crawl()
    print("URLs found:", urls)
    return urls

def collect_task(**context):
    urls = context['ti'].xcom_pull(task_ids='crawl_urls')
    collector = CollectorAgent()
    data = collector.collect(urls)
    print("Collected data:", data[:2])  # imprime só os 2 primeiros

def process_task(**context):
    collector_data = context['ti'].xcom_pull(task_ids='collect_recipes')
    processor = ProcessingAgent()
    processed = [processor.process(d["html"]) for d in collector_data]
    print("Processed data:", processed[:2])

def embedding_task(**context):
    processed_data = context['ti'].xcom_pull(task_ids='process_recipes')
    embedder = EmbeddingAgent()
    embeddings = [embedder.generate_embedding(d["text"]) for d in processed_data]
    print("Embeddings sample:", embeddings[0][:10])

with DAG(
    "recipe_rag_pipeline",
    start_date=datetime(2026, 3, 10),
    schedule_interval="@daily",
    catchup=False
) as dag:

    crawl = PythonOperator(task_id="crawl_urls", python_callable=crawl_task)
    collect = PythonOperator(task_id="collect_recipes", python_callable=collect_task, provide_context=True)
    process = PythonOperator(task_id="process_recipes", python_callable=process_task, provide_context=True)
    embed = PythonOperator(task_id="generate_embeddings", python_callable=embedding_task, provide_context=True)

    crawl >> collect >> process >> embed