from prod_assistant.mcp_servers.product_search_saver import mcp


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
