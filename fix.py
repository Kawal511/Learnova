import sys
with open('d:\\IPD_Project\\learnova\\app.py', 'r', encoding='utf-8') as f:
    c = f.read()

import re
c = re.sub(r'images_to_describe = \[\]\s*for i, c in enumerate\(chunks\):.*?c\["text"\] \+ "\\n\\n\[Visual Image Context: " \+ desc_map\[i\] \+ "\]"',
r'''images_to_describe = []
                seen_image_keys = set()
                for i, chunk_data in enumerate(chunks):
                    if "image" in chunk_data and chunk_data["image"]:
                        img_key = len(chunk_data["image"]["bytes"])
                        if img_key not in seen_image_keys:
                            seen_image_keys.add(img_key)
                            images_to_describe.append({
                                "index": i,
                                "bytes": chunk_data["image"]["bytes"],
                                "ext": chunk_data["image"].get("ext", "png")
                            })
                
                if images_to_describe:
                    with st.spinner(f"🔍 Analyzing {len(images_to_describe)} unique images with Gemini Vision..."):
                        described_data = describe_images(images_to_describe)
                        for chunk_data in chunks:
                            if "image" in chunk_data and chunk_data["image"]:
                                desc = next((d["description"] for d in described_data if d["bytes"] == chunk_data["image"].get("bytes")), None)
                                if desc:
                                    chunk_data["image"]["description"] = desc
                                    # Provide this context to the Groq Improver too
                                    chunk_data["text"] = chunk_data["text"] + "\\n\\n[Visual Image Context: " + desc + "]"''', c, flags=re.DOTALL)
with open('d:\\IPD_Project\\learnova\\app.py', 'w', encoding='utf-8') as f:
    f.write(c)
print("Replaced!")
