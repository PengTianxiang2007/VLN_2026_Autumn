"""Codex stdio MCP tools for an attached VLNVerse H1 (Python MCP SDK 2.x)."""
import argparse
import json
import socket
import uuid
from pathlib import Path
from typing import Literal

from mcp.server.mcpserver import Context, Image, MCPServer
from mcp_types import CallToolResult, TextContent, ToolAnnotations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", type=Path, required=True)
    args = parser.parse_args()
    endpoint = json.loads(args.endpoint.read_bytes())
    if endpoint["status"] != "ready":
        raise RuntimeError("The selected H1 tool service is detached.")
    server = MCPServer("vlnverse")
    client_id = uuid.uuid4()

    def call(method, action, ctx):
        request_id = str(uuid.uuid5(client_id, str(ctx.request_id)))
        request = dict(id=request_id, method=method, action=action)
        with socket.socket(socket.AF_UNIX) as conn:
            conn.settimeout(120)
            conn.connect(endpoint["socket"])
            conn.sendall(json.dumps(request).encode() + b"\n")
            with conn.makefile("rb") as response:
                reply = json.loads(response.readline(65536))
        if "error" in reply:
            raise ValueError(reply["error"])
        result = reply["result"]
        image = args.endpoint.parent / "frames" / f"{result['sequence']:05d}.png"
        return CallToolResult(content=[
            TextContent(type="text", text=json.dumps(result)),
            Image(path=image).to_image_content(),
        ])

    @server.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False))
    def observe(ctx: Context) -> CallToolResult:
        """See the current 640x480 H1 front RGB at this action boundary. Advances zero physics ticks."""
        return call("observe", None, ctx)

    @server.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False,
                                             idempotentHint=False, openWorldHint=False))
    def step(action: Literal["forward", "turn_left", "turn_right", "finish_return"], ctx: Context) -> CallToolResult:
        """Execute one native H1 movement and return the resulting front RGB and status.
        finish_return declares that the completion condition in the current task has been met.
        It closes local movement without ending the navigation episode.
        """
        return call("step", action, ctx)

    server.run(transport="stdio")


if __name__ == "__main__":
    main()
