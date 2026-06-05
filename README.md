


# 🎬 CineGet v3 — Movie & Documentary Downloader

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Google%20Colab-orange.svg)](https://colab.research.google.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

`CineGet v3` is an interactive, high-performance command-line and GUI hybrid utility explicitly architected to turn your **Google Colab** instance into a fast media curation sandbox. Utilizing Colab's high-bandwidth datacenter backbone network pipelines, it searches across multiple indexes simultaneously, renders metadata in stylized HTML elements, and pulls down files via parallelized `aria2c` streams.

> ⚠️ **LEGAL DISCLAIMER:** Only download content you own or have explicit legal rights to. Public-domain and Creative Commons films are freely downloadable. Please respect copyright laws in your local jurisdiction.

---

## ✨ Key Features

* **Multi-Engine Aggregation:** Queries 6 distinct public scrapers and DHT index API setups (`YTS`, `Knaben`, `Solidtorrents`, `BTDIG`, `ThePirateBay`, `1337x`) simultaneously.
* **Intelligent Deduplication:** Automatically normalizes metadata, strips out extraneous punctuation/years, sorts by swarm health, and presents the best options seamlessly.
* **Rich HTML Display Components:** Injects beautifully designed modern CSS cards directly into Colab output logs to view ratings, genres, and contextual text formatting summaries.
* **High-Speed Core Engine:** Uses `aria2c` instead of basic download managers to support multi-connection segmentation, maximizing processing efficiency.
* **Automation Modules:** Integrates subtitle tracking mechanisms (`subliminal`) to isolate, verify, and match proper English subtitles instantly based on hash variations.

---
## Output Image
<img width="1716" height="603" alt="Image" src="https://github.com/user-attachments/assets/3ae5e015-8841-410a-8e72-6b0371a7554e" />
<img width="1527" height="692" alt="Image" src="https://github.com/user-attachments/assets/fa52c839-1f86-4fd2-811e-6eac4310e7ab" />

## 🛠️ Supported Indexes

| Source | Target Type Focus | API/Scraper Type | Swarm Health Metrics |
| :--- | :--- | :--- | :--- |
| **YTS.mx** | Mainstream Cinema | Rich JSON API | Exceptionally High |
| **Knaben** | Meta-Search Aggregator | Unified JSON API Endpoint | High |
| **Solidtorrents**| Documentary Libraries | Native REST API Platform | Good |
| **BTDIG** | Obscure/Niche Media | Live DHT Crawler | Real-time discovery |
| **ThePirateBay** | General Archive Backups | Proxy API Pipeline | Moderate |
| **1337x** | High-Fidelity Video | Live DOM Scraping Fallback | Stable |

---

```python
!wget -q [https://raw.githubusercontent.com/Yonatankinfe/Cineget-v3/main/movie_downloader_colab.py](https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO_NAME/main/movie_downloader_colab.py) -O cineget.py
exec(open('cineget.py').read())

