def paginate(query, page: int, per_page: int):
    page = max(1, page)
    per_page = min(max(1, per_page), 50)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return {
        "items": pagination.items,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
    }


def cursor_paginate(query, cursor_field, cursor, limit: int, descending: bool = True):
    q = query
    if cursor is not None:
        if descending:
            q = q.filter(cursor_field < cursor)
        else:
            q = q.filter(cursor_field > cursor)
    order = cursor_field.desc() if descending else cursor_field.asc()
    items = q.order_by(order).limit(limit + 1).all()
    has_more = len(items) > limit
    items = items[:limit]
    next_cursor = getattr(items[-1], "id", None) if items and has_more else None
    return {"items": items, "next_cursor": str(next_cursor) if next_cursor else None}
