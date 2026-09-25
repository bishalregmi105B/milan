import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:milan/app/theme/color_tokens.dart';
import 'package:milan/shared/widgets/swipe_card.dart';

Widget _card({
  required SwipeCardController controller,
  Future<bool> Function()? onLike,
  Future<bool> Function()? onPass,
  Future<bool> Function()? onSuperlike,
}) {
  return MaterialApp(
    theme: milanLightTheme(),
    home: Scaffold(
      body: SwipeCard(
        key: ValueKey(controller),
        controller: controller,
        mediaUrls: const [],
        name: 'Test',
        age: 25,
        onLike: onLike,
        onPass: onPass,
        onSuperlike: onSuperlike,
      ),
    ),
  );
}

void main() {
  testWidgets('pass invokes only the pass callback', (tester) async {
    final controller = SwipeCardController();
    var likes = 0;
    var passes = 0;
    var superlikes = 0;
    await tester.pumpWidget(
      _card(
        controller: controller,
        onLike: () async {
          likes++;
          return true;
        },
        onPass: () async {
          passes++;
          return true;
        },
        onSuperlike: () async {
          superlikes++;
          return true;
        },
      ),
    );

    controller.pass();
    await tester.pumpAndSettle();

    expect(likes, 0);
    expect(passes, 1);
    expect(superlikes, 0);
  });

  testWidgets('like and superlike use distinct callbacks', (tester) async {
    final controller = SwipeCardController();
    var likes = 0;
    var passes = 0;
    var superlikes = 0;
    await tester.pumpWidget(
      _card(
        controller: controller,
        onLike: () async {
          likes++;
          return true;
        },
        onPass: () async {
          passes++;
          return true;
        },
        onSuperlike: () async {
          superlikes++;
          return true;
        },
      ),
    );

    controller.like();
    await tester.pumpAndSettle();
    expect(likes, 1);

    // A successful card is removed by its parent in the real deck. Recreate
    // it here before checking the next command path.
    final nextController = SwipeCardController();
    await tester.pumpWidget(
      _card(
        controller: nextController,
        onLike: () async {
          likes++;
          return true;
        },
        onPass: () async {
          passes++;
          return true;
        },
        onSuperlike: () async {
          superlikes++;
          return true;
        },
      ),
    );
    nextController.superlike();
    await tester.pumpAndSettle();

    expect(likes, 1);
    expect(passes, 0);
    expect(superlikes, 1);
  });

  testWidgets('duplicate commands do not commit twice', (tester) async {
    final controller = SwipeCardController();
    var calls = 0;
    await tester.pumpWidget(
      _card(
        controller: controller,
        onPass: () async {
          calls++;
          return true;
        },
      ),
    );

    controller.pass();
    controller.pass();
    await tester.pumpAndSettle();

    expect(calls, 1);
  });

  testWidgets('rejected action restores the card for retry', (tester) async {
    final controller = SwipeCardController();
    var calls = 0;
    await tester.pumpWidget(
      _card(
        controller: controller,
        onPass: () async {
          calls++;
          return calls > 1;
        },
      ),
    );

    controller.pass();
    await tester.pumpAndSettle();
    expect(calls, 1);

    controller.pass();
    await tester.pumpAndSettle();
    expect(calls, 2);
  });
}
