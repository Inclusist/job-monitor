@app.route('/api/search-queries')
@login_required
def api_search_queries():
    """Get user's search queries for prefilling preferences"""
    user = get_user()
    user_id = user['id']
    
    queries = cv_manager.get_user_search_queries(user_id, active_only=True)
    
    # Extract unique titles and locations from queries
    titles = set()
    locations = set()
    work_arrangement = None
    
    for query in queries:
        if query.get('title_keywords'):
            titles.add(query['title_keywords'])
        if query.get('location'):
            locations.add(query['location'])
        if not work_arrangement and query.get('work_arrangement'):
            work_arrangement = query['work_arrangement']
    
    return jsonify({
        'titles': list(titles),
        'locations': list(locations),
        'work_arrangement': work_arrangement,
        'query_count': len(queries)
    })
