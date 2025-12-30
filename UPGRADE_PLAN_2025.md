# Philly Sports News - Modernization Plan 2025/2026

## Current Issues Identified
1. **Incomplete Article Cards**: Some cards (Liberty Ballers, Philadelphia Sixers) show blank/placeholder images
2. **Static Source Names**: Source names are hardcoded in templates
3. **No Fallback System**: Incomplete articles are still displayed
4. **Scraping Reliability**: Web scraping is fragile and breaks when sites change

## Research Findings

### Modern Alternatives (2025/2026)
1. **RSS Feeds**: More reliable than scraping, standardized format
   - Liberty Ballers: `https://www.libertyballers.com/rss/current`
   - Most news sites provide RSS feeds
   - Better structured data (title, description, image, date)

2. **Hybrid Approach**: Combine RSS feeds + scraping for sources without RSS
   - RSS for primary sources (more reliable)
   - Scraping as fallback for sources without RSS

3. **Article Validation**: Only show articles with complete data
   - Title ✅
   - Image ✅
   - Description ✅
   - URL ✅

## Iterative Upgrade Plan

### Phase 1: Immediate Fixes (Week 1)
**Goal**: Fix blank cards and implement fallback system

1. ✅ **Enhanced Article Filtering**
   - Filter out articles missing image or description
   - Only display fully populated articles
   - Implement article quality scoring

2. ✅ **Dynamic Source Names**
   - Extract source name from article metadata
   - Remove hardcoded source names from templates
   - Fallback to site domain if no source found

3. ✅ **Article Pool System**
   - Collect all articles from all sources
   - Score articles by completeness (title + image + description + author)
   - Display only top-scoring articles
   - If a source has incomplete articles, use articles from other sources

### Phase 2: RSS Feed Integration (Week 2-3)
**Goal**: Replace unreliable scraping with RSS feeds where available

1. **RSS Feed Parser**
   - Install `feedparser` library
   - Create RSS feed scraper class
   - Support multiple feed formats (RSS 2.0, Atom)

2. **Source Migration**
   - Identify which sources have RSS feeds
   - Migrate Liberty Ballers to RSS (has reliable feed)
   - Keep scraping as fallback for sources without RSS

3. **Unified Article Interface**
   - Create common article data structure
   - Both RSS and scraping populate same structure
   - Transparent to frontend

### Phase 3: Enhanced Features (Week 4-5)
**Goal**: Modern features for 2025/2026

1. **Caching System**
   - Implement Redis or in-memory caching
   - Cache articles for 1 hour
   - Reduce redundant requests

2. **Background Jobs**
   - Move article fetching to background tasks
   - Use Celery or similar for async processing
   - Faster page loads

3. **Article Freshness**
   - Prioritize recent articles
   - Show publication dates
   - Auto-refresh every hour

### Phase 4: Advanced Features (Week 6+)
**Goal**: Production-ready features

1. **Error Handling & Monitoring**
   - Comprehensive error logging
   - Health checks for all sources
   - Alert on source failures

2. **Performance Optimization**
   - Database for article storage
   - Pagination for large article lists
   - CDN for images

3. **User Experience**
   - Article preview on hover
   - Share buttons
   - Reading time estimates

## Implementation Priority

### High Priority (Fix Now)
1. ✅ Filter incomplete articles
2. ✅ Use fully populated articles from other sources
3. ✅ Dynamic source names

### Medium Priority (Next 2 Weeks)
1. RSS feed integration for Liberty Ballers
2. Unified article interface
3. Caching system

### Low Priority (Future)
1. Background job processing
2. Database storage
3. Advanced UX features

## Technical Stack Recommendations

### Current Stack
- Flask (web framework)
- BeautifulSoup (scraping)
- Requests (HTTP)

### Recommended Additions
- `feedparser` (RSS parsing)
- `Flask-Caching` or `Redis` (caching)
- `Celery` (background tasks, optional)
- `SQLite` or `PostgreSQL` (article storage, optional)

## Success Metrics

1. **Article Completeness**: 100% of displayed articles have all fields
2. **Source Reliability**: RSS feeds reduce scraping failures by 80%
3. **Page Load Time**: < 2 seconds with caching
4. **Uptime**: 99%+ with proper error handling

## Next Steps

1. Implement Phase 1 fixes (this week)
2. Test RSS feed integration for Liberty Ballers
3. Gradually migrate other sources to RSS
4. Monitor and iterate based on results

