def categorize_items(item_list, remote_items=None, mock_items=None):
    """
    Core function: categorize any list of items into Mock/Plugin/Remote.

    Args:
        item_list: List of items to categorize
        remote_items: Custom set of remote items (optional)
        mock_items: Custom set of mock items (optional)

    Returns: dict {category: [items]} with only non-empty categories
    """
    remote_items = remote_items or REMOTE_ITEMS
    mock_items = mock_items or MOCK_ITEMS

    categorized = {'Remote': [], 'Mock': [], 'Plugin': []}

    for item in item_list:
        if item in remote_items:
            categorized['Remote'].append(item)
        elif item in mock_items or 'mock' in item.lower():
            categorized['Mock'].append(item)
        else:
            categorized['Plugin'].append(item)

    # Return only non-empty categories
    return {k: v for k, v in categorized.items() if v}

