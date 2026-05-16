#!/bin/bash
# Inverion Marker Push Script
# Usage: ./push_markers.sh [source]
# Sources: all, gdelt, rss, newsapi, bing, reddit, google

set -e

# Configuration
WP_SITE="https://kylosarc.com"
WP_USER="minimaxman"
WP_PASS="[w@nk0w0nk]"

# Log directory
LOG_DIR="logs"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/push_${TIMESTAMP}.log"

# Function to push markers from a source
push_source() {
    local source=$1
    shift
    echo "[$(date)] Starting $source push..." >> "$LOG_FILE"
    python3 server.py "$@" --push-markers --wp-site "$WP_SITE" --wp-user "$WP_USER" --wp-pass "$WP_PASS" 2>&1 | tee -a "$LOG_FILE"
    echo "[$(date)] Completed $source" >> "$LOG_FILE"
}

# RSS Feeds - News
RSS_NEWS=(
    "https://feeds.bbci.co.uk/news/rss.xml"
    "https://feeds.reuters.com/reuters/topNews"
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"
    "https://www.theguardian.com/world/rss"
    "https://feeds.arstechnica.com/arstechnica/index"
    "https://www.bing.com/news/search?format=RSS&q=trump"
    "https://www.bing.com/news/search?format=RSS&q=politics"
    "https://thehill.com/homenews/feed/"
    "https://www.vox.com/rss/world-politics/index.xml"
    "https://abcnews.go.com/abcnews/internationalheadlines"
    "https://nypost.com/feed/"
    "https://theconversation.com/us/articles.atom"
    "https://www.pbs.org/newshour/feeds/rss/politics"
)

# RSS Feeds - Government/Legal
RSS_GOVT=(
    "https://www.epa.gov/newsreleases/search/rss"
    "https://www.federalregister.gov/api/v1/documents.rss"
)

# RSS Feeds - Reddit
RSS_REDDIT=(
    "https://www.reddit.com/search.rss?sort=new&q=trump"
    "https://www.reddit.com/search.rss?sort=new&q=politics"
    "https://www.reddit.com/search.rss?sort=new&q=science"
)

# Push based on argument
case "${1:-all}" in
    all)
        echo "=== Pushing from ALL sources ===" | tee -a "$LOG_FILE"
        
        # RSS News feeds
        for feed in "${RSS_NEWS[@]}"; do
            echo "Fetching RSS: $feed" | tee -a "$LOG_FILE"
            push_source "rss" --rss "$feed"
            sleep 3
        done
        
        # RSS Government feeds
        for feed in "${RSS_GOVT[@]}"; do
            echo "Fetching RSS: $feed" | tee -a "$LOG_FILE"
            push_source "rss" --rss "$feed"
            sleep 3
        done
        
        # GDELT topics
        for topic in "climate" "technology" "politics" "science"; do
            push_source "gdelt-$topic" --gdelt "$topic"
            sleep 15  # GDELT rate limit
        done
        
        # Bing news
        for query in "world news" "technology" "science"; do
            push_source "bing-$query" --bing "$query"
            sleep 3
        done
        
        echo "=== All sources complete ===" | tee -a "$LOG_FILE"
        ;;
    gdelt)
        for topic in "climate" "technology" "politics" "science"; do
            push_source "gdelt-$topic" --gdelt "$topic"
            sleep 15
        done
        ;;
    rss)
        echo "Fetching RSS feeds..." | tee -a "$LOG_FILE"
        for feed in "${RSS_NEWS[@]}"; do
            echo "  $feed" | tee -a "$LOG_FILE"
            push_source "rss" --rss "$feed"
            sleep 3
        done
        for feed in "${RSS_GOVT[@]}"; do
            echo "  $feed" | tee -a "$LOG_FILE"
            push_source "rss" --rss "$feed"
            sleep 3
        done
        ;;
    newsapi)
        for query in "climate change" "technology" "science"; do
            push_source "newsapi-$query" --newsapi "$query"
            sleep 60
        done
        ;;
    bing)
        for query in "world news" "technology" "science"; do
            push_source "bing-$query" --bing "$query"
            sleep 3
        done
        ;;
    reddit)
        for feed in "${RSS_REDDIT[@]}"; do
            push_source "reddit" --rss "$feed"
            sleep 3
        done
        ;;
    google)
        for query in "climate" "technology" "science"; do
            push_source "google-$query" --google "$query"
            sleep 90
        done
        ;;
    *)
        echo "Usage: $0 [all|gdelt|rss|newsapi|bing|reddit|google]"
        exit 1
        ;;
esac

echo "Done. See $LOG_FILE for details."