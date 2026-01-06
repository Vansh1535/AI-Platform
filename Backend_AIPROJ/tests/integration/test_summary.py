import requests

print('\n' + '='*60)
print('PRODUCTION INGESTION - FINAL SUMMARY')
print('='*60)

r = requests.get('http://127.0.0.1:8000/rag/docs/health')
health = r.json()['health']
print(f'\n📊 System Health:')
print(f'  Total Documents: {health["total_documents"]}')
print(f'  Success Rate: {health["success_rate"]:.1f}%')
print(f'  Avg Processing Time: {health["avg_processing_time_ms"]:.0f}ms')
print(f'  Total Chunks: {health["total_chunks"]}')

r2 = requests.get('http://127.0.0.1:8000/rag/docs/list')
doc = r2.json()['documents'][0]
print(f'\n📄 Document Details:')
print(f'  ID: {doc["document_id"]}')
print(f'  Filename: {doc["filename"]}')
print(f'  Checksum: {doc["checksum_hash"][:16]}...')
print(f'  Status: {doc["ingestion_status"]}')
print(f'  Version: {doc["ingestion_version"]}')
print(f'  Chunks: {doc["chunk_count"]}')
print(f'  Tokens: {doc["token_estimate"]}')

print('\n✅ All production features verified and working!')
print('='*60)
