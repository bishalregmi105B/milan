import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path/path.dart' as p;
import 'package:sqflite/sqflite.dart';

/// Offline cache (doc 3 §1): matches, chat history, resolved chat themes.
/// sqflite over drift per doc 3 §2 — less code-gen for the same job.
class LocalDb {
  Database? _db;

  Future<Database> get database async {
    _db ??= await _open();
    return _db!;
  }

  Future<Database> _open() async {
    final dir = await getDatabasesPath();
    return openDatabase(
      p.join(dir, 'milan.db'),
      // v2: media_type + read_at on chat_messages (doc 8 §A2.6/§A2.12 — the
      // client needs media kind and read receipts in cached rows too).
      version: 2,
      onCreate: (db, version) async {
        await db.execute('''
          CREATE TABLE chat_messages (
            id TEXT PRIMARY KEY,
            match_id TEXT NOT NULL,
            sender_id TEXT NOT NULL,
            body TEXT,
            media_url TEXT,
            media_type TEXT,
            read_at TEXT,
            is_ai_suggested INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
          )
        ''');
        await db.execute(
            'CREATE INDEX idx_chat_messages_match ON chat_messages(match_id)');
        await db.execute('''
          CREATE TABLE resolved_themes (
            scope_key TEXT PRIMARY KEY,
            theme_json TEXT NOT NULL,
            synced INTEGER DEFAULT 0
          )
        ''');
        await db.execute('''
          CREATE TABLE interview_progress (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            state_json TEXT NOT NULL
          )
        ''');
      },
      onUpgrade: (db, oldVersion, newVersion) async {
        if (oldVersion < 2) {
          await db.execute('ALTER TABLE chat_messages ADD COLUMN media_type TEXT');
          await db.execute('ALTER TABLE chat_messages ADD COLUMN read_at TEXT');
        }
      },
    );
  }

  Future<void> cacheMessage(Map<String, Object?> row) async {
    final db = await database;
    await db.insert('chat_messages', row,
        conflictAlgorithm: ConflictAlgorithm.replace);
  }

  Future<List<Map<String, Object?>>> messagesForMatch(String matchId) async {
    final db = await database;
    return db.query('chat_messages',
        where: 'match_id = ?', whereArgs: [matchId], orderBy: 'created_at');
  }

  /// Doc 3 §4 themeProvider: optimistic local write so theme changes are
  /// instant and work offline; [synced] flips once the backend confirms.
  Future<void> saveResolvedTheme(String scopeKey, Map<String, dynamic> json,
      {bool synced = false}) async {
    final db = await database;
    await db.insert(
      'resolved_themes',
      {'scope_key': scopeKey, 'theme_json': jsonEncode(json), 'synced': synced ? 1 : 0},
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  Future<Map<String, dynamic>?> loadResolvedTheme(String scopeKey) async {
    final db = await database;
    final rows = await db.query('resolved_themes',
        where: 'scope_key = ?', whereArgs: [scopeKey], limit: 1);
    if (rows.isEmpty) return null;
    return jsonDecode(rows.first['theme_json'] as String) as Map<String, dynamic>;
  }

  Future<List<String>> unsyncedScopeKeys() async {
    final db = await database;
    final rows = await db
        .query('resolved_themes', where: 'synced = 0', columns: ['scope_key']);
    return rows.map((r) => r['scope_key'] as String).toList();
  }

  Future<void> markThemesSynced() async {
    final db = await database;
    await db.update('resolved_themes', {'synced': 1});
  }

  Future<void> saveInterviewProgress(String stateJson) async {
    final db = await database;
    await db.insert(
      'interview_progress',
      {'id': 1, 'state_json': stateJson},
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  Future<String?> loadInterviewProgress() async {
    final db = await database;
    final rows = await db.query('interview_progress', limit: 1);
    return rows.isEmpty ? null : rows.first['state_json'] as String?;
  }
}

final localDbProvider = Provider<LocalDb>((ref) => LocalDb());
