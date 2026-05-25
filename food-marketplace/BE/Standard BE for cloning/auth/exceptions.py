from fastapi import HTTPException, status


def permission_denied():
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Permission denied",
    )


def unauthorized():
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="メールアドレスまたはパスワードが正しくありません",
    )


def invalid_shop_credentials():
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="店舗ID、メールアドレスまたはパスワードが正しくありません",
    )
