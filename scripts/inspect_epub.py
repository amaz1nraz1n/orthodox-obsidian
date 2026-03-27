import zipfile

epub_path = './source_files/Full Bible/The Orthodox Study Bible (St. Athanasius Academy of Orthodox Theology.epub'

with zipfile.ZipFile(epub_path, 'r') as z:
    content = z.read('OEBPS/Daniel.html').decode('utf-8', errors='ignore')
    # Find the end of chapter 12 and start of Susanna
    print(content[content.find('id="Dan_vchap12-1"')-100:content.find('id="Dan_vchap12-1"')+500])
    print("\n...\n")
    print(content[content.find('id="Sus_vchap1-1"')-100:content.find('id="Sus_vchap1-1"')+500])
    print("\n...\n")
    print(content[content.find('id="Bel_vchap1-1"')-100:content.find('id="Bel_vchap1-1"')+500])
