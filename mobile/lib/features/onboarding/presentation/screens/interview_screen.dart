import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme/color_tokens.dart';
import '../../../../app/theme/spacing_tokens.dart';
import '../../../../core/localization/app_localizations.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/storage/local_db.dart';
import '../../../../shared/widgets/chat_bubble.dart';

/// Screen 9 — conversational interview rendered as a chat thread over a
/// structured data-collection flow. Partial progress persists locally so a
/// dropped connection never restarts the whole interview (doc 3 §6).
class InterviewScreen extends ConsumerStatefulWidget {
  const InterviewScreen({super.key});

  @override
  ConsumerState<InterviewScreen> createState() => _InterviewScreenState();
}

class _InterviewQuestion {
  const _InterviewQuestion(this.key, this.question, {this.quickReplies = const []});
  final String key;
  final String question;
  final List<String> quickReplies;
}

class _InterviewScreenState extends ConsumerState<InterviewScreen> {
  static const _questions = <_InterviewQuestion>[
    _InterviewQuestion('intent', 'What are you hoping to find here?',
        quickReplies: ['Something serious', 'Something casual', 'Still figuring it out']),
    _InterviewQuestion('weekend', "What does a good weekend look like for you?"),
    _InterviewQuestion('values', "What's one value you won't compromise on?"),
    _InterviewQuestion('dealbreaker', 'Any absolute dealbreakers?', quickReplies: ['Smoking', 'Dishonesty', 'None']),
    _InterviewQuestion('style', 'How do you usually talk — direct, playful, or thoughtful?',
        quickReplies: ['Direct', 'Playful', 'Thoughtful']),
  ];

  final _composer = TextEditingController();
  int _step = 0;
  bool _sending = false;
  bool _finalizing = false;
  final Map<String, dynamic> _answers = {};

  @override
  void initState() {
    super.initState();
    _restore();
  }

  Future<void> _restore() async {
    final raw = await ref.read(localDbProvider).loadInterviewProgress();
    if (raw == null) return;
    final saved = jsonDecode(raw) as Map<String, dynamic>;
    if (!mounted) return;
    setState(() {
      _step = (saved['step'] as int?) ?? 0;
      _answers.addAll((saved['answers'] as Map<String, dynamic>?) ?? {});
    });
  }

  Future<void> _persist() async {
    await ref.read(localDbProvider).saveInterviewProgress(
          jsonEncode({'step': _step, 'answers': _answers}),
        );
  }

  Future<void> _submit(String answer) async {
    if (_sending) return;
    final question = _questions[_step];
    setState(() {
      _answers[question.key] = answer;
      _step++;
      _sending = true;
    });
    await _persist();

    // Structured extraction per completed interview (doc 5 §3.1).
    try {
      await ref.read(apiClientProvider).post('/profile/interview/signal', body: {
        'qa_pairs': [
          {'question': question.question, 'answer': answer},
        ],
        'partial': true,
      });
    } on AppException {
      // extraction retries server-side on completion; flow continues offline
    }
    if (mounted) setState(() => _sending = false);
  }

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    final l10n = AppLocalizations.of(context)!;
    final done = _step >= _questions.length;

    return Scaffold(
      appBar: AppBar(title: Text(l10n.onboardingInterviewTitle)),
      body: Column(children: [
        LinearProgressIndicator(
          value: done ? 1 : _step / _questions.length,
          minHeight: 3,
          color: milan.marigold500,
        ),
        Expanded(
          child: ListView(
            padding: EdgeInsets.symmetric(vertical: Spacing.lg),
            children: [
              for (var i = 0; i <= (_step < _questions.length ? _step : _questions.length - 1); i++) ...[
                ChatBubble(
                  text: _questions[i].question,
                  isSent: false,
                  isAi: true,
                  bubbleColor: milan.dhaka100,
                ),
                if (_answers.containsKey(_questions[i].key))
                  ChatBubble(text: _answers[_questions[i].key]!, isSent: true),
              ],
            ],
          ),
        ),
        SafeArea(
          top: false,
          child: Padding(
            padding: EdgeInsets.all(Spacing.lg),
            child: done
                ? FilledButton(
                    onPressed: _finalizing
                        ? null
                        : () async {
                            // FINAL submit: partial=false stamps
                            // interview_completed_at server-side and runs the
                            // full-signal extraction that powers matching.
                            setState(() => _finalizing = true);
                            try {
                              await ref.read(apiClientProvider).post(
                                  '/profile/interview/signal',
                                  body: {
                                      'qa_pairs': [
                                        for (final q in _questions)
                                          if (_answers[q.key] != null)
                                            {'question': q.question, 'answer': _answers[q.key]},
                                      ],
                                      'partial': false,
                                    });
                            } on AppException {
                              // flow continues even if the final extraction
                              // fails — partial batches already saved the data
                            }
                            if (!mounted) return;
                            context.go('/onboarding/location-primer');
                          },
                    child: Text(_finalizing ? 'Saving…' : l10n.commonContinue))
                : Column(mainAxisSize: MainAxisSize.min, children: [
                    Wrap(spacing: Spacing.md, children: [
                      for (final quick in _questions[_step].quickReplies)
                        ActionChip(label: Text(quick), onPressed: () => _submit(quick)),
                    ]),
                    SizedBox(height: Spacing.md),
                    Row(children: [
                      Expanded(
                        child: TextField(
                          controller: _composer,
                          decoration: const InputDecoration(hintText: 'Type your answer…'),
                          onSubmitted: (v) {
                            if (v.trim().isNotEmpty) {
                              _submit(v.trim());
                              _composer.clear();
                            }
                          },
                        ),
                      ),
                      IconButton(icon: Icon(Icons.send, color: milan.marigold500), onPressed: () {
                        if (_composer.text.trim().isNotEmpty) {
                          _submit(_composer.text.trim());
                          _composer.clear();
                        }
                      }),
                    ]),
                  ]),
          ),
        ),
      ]),
    );
  }
}
