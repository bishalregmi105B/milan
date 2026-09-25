from datetime import date

from app import create_app
from app.extensions import db

app = create_app("prod")
with app.app_context():
    from app.models import PaymentQrCode, Photo, Profile, Reel, User
    from app.services import image_gen_service

    # 1) demo QRs (clearly-watermarked test QR images so the checkout flow is
    # testable; replace via the admin Payments page with real merchant QRs)
    for method in ("esewa", "khalti", "fonepay", "connectips"):
        qr = PaymentQrCode.query.filter_by(method=method).first()
        if qr is None:
            qr = PaymentQrCode(method=method)
            db.session.add(qr)
        if not qr.image_url:
            try:
                img = image_gen_service.generate_image(
                    f"simple TEST payment QR code placeholder for {method}, flat design, "
                    "large TEST WATERMARK across it, not a real payable code",
                    width=512, height=512)
            except Exception as exc:
                print("qr gen failed:", method, str(exc)[:60])
                continue
            qr.image_url = img["url"]
            qr.account_label = f"Milan TEST — {method} (demo, replace via admin)"
            qr.instructions = (
                f"DEMO QR for testing the flow — scan with the {method} app for "
                "real after admin uploads the merchant QR.")
            qr.is_active = True
            print("qr seeded:", method)
    db.session.commit()

    # 2) demo jhalaks: demo users with AI-illustrated avatars + approved reels
    demo_specs = [
        ("demo.sunita", "Sunita", "aaja ko vibe ✨"),
        ("demo.bikash", "Bikash", "hills > everything"),
        ("demo.anisha", "Anisha", "chiya o'clock ☕"),
    ]
    for handle, name, caption in demo_specs:
        u = User.query.filter(User.email == f"{handle}@milanapp.live").first()
        if u is None:
            u = User(email=f"{handle}@milanapp.live", auth_provider="demo",
                     is_verified=True, gender="female", date_of_birth=date(1999, 5, 14))
            db.session.add(u)
            db.session.flush()
            db.session.add(Profile(user_id=u.id, display_name=name,
                                   bio="Just here for the vibes ✨", city="Kathmandu"))
            db.session.commit()
        if not u.photos:
            try:
                img = image_gen_service.generate_image(
                    f"casual illustrated portrait of a young Nepali woman named {name}, "
                    "smiling, full face visible, stylized art, not photorealistic",
                    width=640, height=640)
                db.session.add(Photo(user_id=u.id, url=img["url"], order_index=0,
                                     moderation_status="approved"))
                db.session.commit()
            except Exception as exc:
                print("avatar failed:", name, str(exc)[:60])
        if Reel.query.filter_by(user_id=u.id).first() is None:
            reel = Reel(
                user_id=u.id,
                video_url="https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyrides.mp4",
                caption=caption,
                moderation_status="approved",
                like_count=hash(name) % 40)
            db.session.add(reel)
            db.session.commit()
            print("reel seeded:", name)
    print("done")
