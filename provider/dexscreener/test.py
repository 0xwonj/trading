import asyncio
import pytest
from provider.dexscreener.client import DexScreenerClient

@pytest.mark.asyncio
async def test_subscribe_without_zyte(capsys):
    client = DexScreenerClient(use_zyte=False, polling_interval=5)

    sub1 = client.subscribe(
        "solana",
        [
            "So11111111111111111111111111111111111111112",
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        ]
    )
    await asyncio.sleep(10)
    captured = capsys.readouterr().out
    assert "Subscription solana:So11111111111111111111111111111111111111112:EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v pairs:" in captured

    sub2 = client.subscribe(
        "solana",
        [
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN"
        ]
    )
    await asyncio.sleep(10)
    captured = capsys.readouterr().out
    assert "Subscription solana:So11111111111111111111111111111111111111112:EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v pairs:" in captured
    assert "Subscription solana:EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v:JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN pairs:" in captured

    client.unsubscribe(sub1)
    await asyncio.sleep(10)
    captured = capsys.readouterr().out
    assert f"Unsubscribed: solana:So11111111111111111111111111111111111111112:EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v" in captured
    assert "Subscription solana:So11111111111111111111111111111111111111112:EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v pairs:" not in captured
    assert "Subscription solana:EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v:JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN pairs:" in captured

    client.unsubscribe(sub2)
    await client.close()

    captured = capsys.readouterr().out
    assert "Unsubscribed: solana:EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v:JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN" in captured

@pytest.mark.asyncio
async def test_subscribe_with_zyte(capsys):
    client = DexScreenerClient(
        use_zyte=True,
        zyte_api_key="e33bbd9e417d4872a9a2cf2731852c7c",
        polling_interval=5
    )

    sub1 = client.subscribe(
        "solana",
        [
            "So11111111111111111111111111111111111111112",
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        ]
    )
    await asyncio.sleep(10)
    captured = capsys.readouterr().out
    assert "Subscription solana:So11111111111111111111111111111111111111112:EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v pairs:" in captured

    sub2 = client.subscribe(
        "solana",
        [
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN"
        ]
    )
    await asyncio.sleep(10)
    captured = capsys.readouterr().out
    assert "Subscription solana:So11111111111111111111111111111111111111112:EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v pairs:" in captured
    assert "Subscription solana:EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v:JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN pairs:" in captured

    client.unsubscribe(sub1)
    await asyncio.sleep(10)
    captured = capsys.readouterr().out
    assert f"Unsubscribed: solana:So11111111111111111111111111111111111111112:EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v" in captured
    assert "Subscription solana:So11111111111111111111111111111111111111112:EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v pairs:" not in captured
    assert "Subscription solana:EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v:JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN pairs:" in captured

    client.unsubscribe(sub2)
    await client.close()

    captured = capsys.readouterr().out
    assert "Unsubscribed: solana:EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v:JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN" in captured
