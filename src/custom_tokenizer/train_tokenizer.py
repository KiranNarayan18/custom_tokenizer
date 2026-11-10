import os
import json
import argparse
from collections.abc import Iterator
from pathlib import Path

from tokenizers import Tokenizer, decoders, models, pre_tokenizers, processors, trainers


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS = os.path.join(ROOT, 'data', 'medical_corpus.txt')
DEFAULT_OUT = os.path.join(ROOT, 'artifacts', 'medical-bpe', 'tokenizer.json')
SPECIAL_TOKENS = ["<|endoftext|>", "<pad>"]


def find_root() -> Path:
    """Repo root (directory that contains data/medical_corpus.txt)."""
    return ROOT


def build_byte_level_bpe() -> Tokenizer:
    """Empty byte-level BPE with GPT-style pretokenizer/decoder"""
    tokenizer = Tokenizer(models.BPE())
    tokenizer.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    tokenizer.decode = decoders.ByteLevel()
    tokenizer.post_processor = processors.ByteLevel(trim_offsets=True)
    return tokenizer


def count_lines(path: Path) -> int:
    """Count non-empty lines (progress length for the trainer)."""
    n = 0
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                n += 1
    return n


def iter_corpus_batches(path: Path, batch_size: int=64) -> Iterator[list[str]]:

    batch: list[str] = []
    with path.open(encoding='utf-8') as handle:
        for line in handle:
            raw = line.strip()
            if not raw: continue
            text = raw
            if raw.startswith("{"):
                try:
                    obj = json.loads(raw)
                    if isinstance(obj, dict) and obj.get('text'):
                        text = str(obj["text"]).strip()
                except json.JSONDecodeError:
                    text = raw
            
            if not raw: continue
            batch.append(text)
            if len(batch) >= batch_size:
                yield batch
                batch = []
    if batch:
        yield batch


def train_byte_level_bpe(corpus: Path, output:Path, vocab_size:int=16000, min_frequency:int=2) -> Tokenizer:
    """Train BPE and save tokenizer.json Returns the trained Tokenizer"""
    if not corpus.is_file():
        raise FileNotFoundError(f"corpus not found: {corpus}")
    tokenizer = build_byte_level_bpe()
    trainer = trainers.BpeTrainer(
        vocab_size=vocab_size,
        min_frequency=min_frequency,
        special_tokens=SPECIAL_TOKENS,
        initial_alphabet=pre_tokenizers.ByteLevel.alphabet(),
        show_progress=True,
    )

    length = count_lines(corpus)
    tokenizer.train_from_iterator(
        iter_corpus_batches(corpus),
        trainer=trainer,
        length=length
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    tokenizer.save(str(output))
    return tokenizer


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--corpus",
        type=Path,
        default=DEFAULT_CORPUS,
        help="UTF-8 text, one document per line",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--vocab-size", type=int, default=16000)
    parser.add_argument("--min-frequency", type=int, default=2)
    args = parser.parse_args()
    tokenizer = train_byte_level_bpe(
        args.corpus.expanduser().resolve(),
        args.out.expanduser().resolve(),
        vocab_size=args.vocab_size,
        min_frequency=args.min_frequency,
    )
    print(f"saved {args.out}  vocab={tokenizer.get_vocab_size()}")


if __name__ == "__main__":
    main()


# uv run python src\custom_tokenizer\train_tokenizer.py --corpus data\pubmed_train.jsonl --out artifacts\medical-bpe-pubmed\tokenizer.json

# uv run python src\custom_tokenizer\train_tokenizer.py --corpus data\general_train.jsonl --out artifacts\general-bpe\tokenizer.json