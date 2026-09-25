import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';


/// Root shell — 4 tab branches + Saathi surfaced as a FAB so it's never more
/// than one tap from any main tab (doc 3 §5).
class MainShell extends StatelessWidget {
  const MainShell({super.key, required this.shell});
  final StatefulNavigationShell shell;

  static const _destinations = [
    (Icons.style_outlined, Icons.style, 'Discover'),
    (Icons.movie_filter_outlined, Icons.movie_filter, 'Jhalak'),
    (Icons.chat_bubble_outline, Icons.chat_bubble, 'Chat'),
    (Icons.person_outline, Icons.person, 'Profile'),
  ];

  @override
  Widget build(BuildContext context) {
    // No FAB: it overlapped the Discover swipe actions, and companions now
    // live in the Chat tab (unified inbox, §14) — one tap from Chat's header.
    return Scaffold(
      body: shell,
      bottomNavigationBar: NavigationBar(
        selectedIndex: shell.currentIndex,
        onDestinationSelected: (i) => shell.goBranch(
          i,
          initialLocation: i == shell.currentIndex,
        ),
        indicatorColor: Theme.of(context).colorScheme.primary.withValues(alpha: 0.12),
        destinations: [
          for (final (icon, activeIcon, label) in _destinations)
            NavigationDestination(
              icon: Icon(icon),
              selectedIcon: Icon(activeIcon, color: Theme.of(context).colorScheme.primary),
              label: label,
            ),
        ],
      ),
    );
  }
}
