from __future__ import annotations

from pydantic import BaseModel, ValidationError


class User(BaseModel):
    name: str
    age: int


def main() -> None:
    raw = {"name": "Alice", "age": "30"}
    try:
        user = User.model_validate(raw)
    except ValidationError as exc:
        print("validation error:")
        print(exc)
        return

    print(user)


if __name__ == "__main__":
    main()
