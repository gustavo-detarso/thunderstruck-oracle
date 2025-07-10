import pickle

with open("db/meta.pkl", "rb") as f:
    meta = pickle.load(f)

tag_to_chunks = {}
for i, m in enumerate(meta):
    for t in m['tags']:
        tag_to_chunks.setdefault(t, []).append((i, m['file']))

for tag, lst in tag_to_chunks.items():
    print(f"TAG: {tag} | Total chunks: {len(lst)}")
    for idx, fname in lst:
        print(f"   - Chunk {idx}: {fname}")
    print()
