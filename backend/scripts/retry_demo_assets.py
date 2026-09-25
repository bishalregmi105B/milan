import time

from app import create_app
from app.extensions import db

app = create_app("prod")
with app.app_context():
    from app.models import PaymentQrCode, Photo, User
    from app.services import image_gen_service

    retried = 0
    for method in ("esewa", "khalti", "fonepay", "connectips"):
        qr = PaymentQrCode.query.filter_by(method=method).first()
        if qr is not None and qr.image_url:
            continue
        if qr is None:
            qr = PaymentQrCode(method=method)
            db.session.add(qr)
        try:
            img = image_gen_service.generate_image(
                f"simple TEST payment QR placeholder for {method}, flat minimal design, "
                "big TEST watermark, not a real payable code", width=512, height=512)
        except Exception as exc:
            print("still failing:", method, str(exc)[:70])
            time.sleep(20)
            continue
        qr.image_url = img["url"]
        qr.account_label = f"Milan TEST — {method} (demo, replace via admin)"
        qr.instructions = (
            f"DEMO QR for testing the flow — replace with the real merchant QR "
            f"via the admin console. Test with the {method} app.")
        qr.is_active = True
        db.session.commit()
        retried += 1
        print("qr seeded:", method)
        time.sleep(15)  # stay under the provider rate limit

    for handle, name in (("demo.sunita", "Sunita"), ("demo.bikash", "Bikash"),
                         ("demo.anisha", "Anisha")):
        u = User.query.filter(User.email == f"{handle}@milanapp.live").first()
        if u is None or u.photos:
            continue
        try:
            img = image_gen_service.generate_image(
                f"casual illustrated portrait of a young Nepali person named {name}, "
                "smiling, full face visible, stylized art, not photorealistic",
                width=640, height=640)
            db.session.add(Photo(user_id=u.id, url=img["url"], order_index=0,
                                 moderation_status="approved"))
            db.session.commit()
            print("avatar done:", name)
        except Exception as exc:
            print("avatar still failing:", name, str(exc)[:70])
        time.sleep(15)
    print("finished, seeded", retried)
