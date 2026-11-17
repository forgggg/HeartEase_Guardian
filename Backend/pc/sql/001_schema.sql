-- 模块2 运行时表结构（库名 heart_ease_pc，由 scripts/init_db.py 创建）
-- 时区：应用写入上海时间，连接建立时 SET time_zone='+08:00'

CREATE TABLE IF NOT EXISTS resume_doc (
  id           VARCHAR(40)  NOT NULL COMMENT 'res_*',
  student_id   VARCHAR(32)  NOT NULL,
  template     VARCHAR(16)  NOT NULL,
  target_role  VARCHAR(64)  NOT NULL DEFAULT '',
  version      INT UNSIGNED NOT NULL DEFAULT 1,
  confirmed    TINYINT(1)   NOT NULL DEFAULT 0,
  needs_review TINYINT(1)   NOT NULL DEFAULT 0,
  doc_json     JSON         NOT NULL,
  created_by   VARCHAR(32)  NOT NULL DEFAULT '',
  created_at   DATETIME(3)  NOT NULL,
  updated_at   DATETIME(3)  NOT NULL,
  PRIMARY KEY (id),
  KEY idx_student_created (student_id, created_at),
  KEY idx_updated (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='简历当前稿';

CREATE TABLE IF NOT EXISTS resume_version (
  id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  resume_id  VARCHAR(40)  NOT NULL,
  version    INT UNSIGNED NOT NULL,
  doc_json   JSON         NOT NULL,
  note       VARCHAR(255) NOT NULL DEFAULT '',
  confirmed  TINYINT(1)   NOT NULL DEFAULT 0,
  created_by VARCHAR(32)  NOT NULL DEFAULT '',
  created_at DATETIME(3)  NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uk_resume_version (resume_id, version),
  CONSTRAINT fk_version_resume FOREIGN KEY (resume_id)
    REFERENCES resume_doc (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='简历版本快照';

CREATE TABLE IF NOT EXISTS resume_analysis (
  id            VARCHAR(40)  NOT NULL,
  student_id    VARCHAR(32)  NOT NULL DEFAULT '',
  filename      VARCHAR(255) NOT NULL DEFAULT '',
  target_role   VARCHAR(64)  NOT NULL DEFAULT '',
  original_text MEDIUMTEXT   NOT NULL,
  revised_text  MEDIUMTEXT   NOT NULL,
  quality_json  JSON         NOT NULL,
  rules_version INT UNSIGNED NOT NULL DEFAULT 0,
  created_by    VARCHAR(32)  NOT NULL DEFAULT '',
  created_at    DATETIME(3)  NOT NULL,
  PRIMARY KEY (id),
  KEY idx_analysis_student (student_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='简历修改记录';

CREATE TABLE IF NOT EXISTS resume_finding (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  analysis_id   VARCHAR(40) NOT NULL,
  seq           INT UNSIGNED NOT NULL,
  rule          VARCHAR(8)  NOT NULL,
  name          VARCHAR(64) NOT NULL,
  severity      ENUM('high','medium','low') NOT NULL,
  original_text TEXT        NOT NULL,
  evidence      VARCHAR(255) NOT NULL DEFAULT '',
  PRIMARY KEY (id),
  UNIQUE KEY uk_finding_seq (analysis_id, seq),
  CONSTRAINT fk_finding_analysis FOREIGN KEY (analysis_id)
    REFERENCES resume_analysis (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='诊断结果';

CREATE TABLE IF NOT EXISTS resume_suggestion (
  analysis_id   VARCHAR(40) NOT NULL,
  suggestion_id VARCHAR(16) NOT NULL COMMENT 's1, s2 ...',
  rule          VARCHAR(8)  NOT NULL,
  rules_json    JSON        NOT NULL,
  original_text TEXT        NOT NULL,
  revised_text  TEXT        NOT NULL,
  reason        TEXT        NOT NULL,
  accepted      TINYINT(1)  NULL,
  decided_by    VARCHAR(32) NULL,
  decided_at    DATETIME(3) NULL,
  PRIMARY KEY (analysis_id, suggestion_id),
  KEY idx_suggestion_rule (rule),
  CONSTRAINT fk_suggestion_analysis FOREIGN KEY (analysis_id)
    REFERENCES resume_analysis (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='逐条修改建议';

CREATE TABLE IF NOT EXISTS upload_file (
  id          VARCHAR(40)  NOT NULL,
  analysis_id VARCHAR(40)  NULL,
  filename    VARCHAR(255) NOT NULL,
  sha256      CHAR(64)     NOT NULL,
  size_bytes  INT UNSIGNED NOT NULL,
  stored_path VARCHAR(512) NOT NULL,
  created_by  VARCHAR(32)  NOT NULL DEFAULT '',
  created_at  DATETIME(3)  NOT NULL,
  PRIMARY KEY (id),
  KEY idx_sha256 (sha256),
  KEY idx_upload_analysis (analysis_id),
  CONSTRAINT fk_upload_analysis FOREIGN KEY (analysis_id)
    REFERENCES resume_analysis (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='上传文件元数据（文件本体在 var/uploads）';

CREATE TABLE IF NOT EXISTS audit_log (
  seq         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '写入顺序，用于同秒排序',
  id          VARCHAR(40) NOT NULL,
  ts          DATETIME(3) NOT NULL,
  actor       VARCHAR(64) NOT NULL DEFAULT '',
  action      VARCHAR(32) NOT NULL,
  target_type VARCHAR(16) NOT NULL,
  target_id   VARCHAR(64) NOT NULL,
  detail      JSON        NOT NULL,
  request_id  VARCHAR(64) NOT NULL DEFAULT '',
  PRIMARY KEY (id),
  UNIQUE KEY uk_audit_seq (seq),
  KEY idx_actor_ts  (actor, ts),
  KEY idx_action_ts (action, ts),
  KEY idx_target_ts (target_id, ts)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='审计日志';
