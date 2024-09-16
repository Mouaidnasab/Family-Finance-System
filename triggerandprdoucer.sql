DELIMITER //
DROP TRIGGER IF EXISTS set_checkbox_to_zero//

CREATE TRIGGER set_checkbox_to_zero
BEFORE UPDATE ON Transactions_Temp
FOR EACH ROW
BEGIN
    IF (
        (NEW.date <> OLD.date OR (NEW.date IS NULL AND OLD.date IS NOT NULL) OR (NEW.date IS NOT NULL AND OLD.date IS NULL)) OR
        (NEW.segment <> OLD.segment OR (NEW.segment IS NULL AND OLD.segment IS NOT NULL) OR (NEW.segment IS NOT NULL AND OLD.segment IS NULL)) OR
        (NEW.type <> OLD.type OR (NEW.type IS NULL AND OLD.type IS NOT NULL) OR (NEW.type IS NOT NULL AND OLD.type IS NULL)) OR
        (NEW.sub_type <> OLD.sub_type OR (NEW.sub_type IS NULL AND OLD.sub_type IS NOT NULL) OR (NEW.sub_type IS NOT NULL AND OLD.sub_type IS NULL)) OR
        (NEW.category <> OLD.category OR (NEW.category IS NULL AND OLD.category IS NOT NULL) OR (NEW.category IS NOT NULL AND OLD.category IS NULL)) OR
        (NEW.sub_category <> OLD.sub_category OR (NEW.sub_category IS NULL AND OLD.sub_category IS NOT NULL) OR (NEW.sub_category IS NOT NULL AND OLD.sub_category IS NULL)) OR
        (NEW.details <> OLD.details OR (NEW.details IS NULL AND OLD.details IS NOT NULL) OR (NEW.details IS NOT NULL AND OLD.details IS NULL)) OR
        (NEW.notes <> OLD.notes OR (NEW.notes IS NULL AND OLD.notes IS NOT NULL) OR (NEW.notes IS NOT NULL AND OLD.notes IS NULL)) OR
        (NEW.sub_notes <> OLD.sub_notes OR (NEW.sub_notes IS NULL AND OLD.sub_notes IS NOT NULL) OR (NEW.sub_notes IS NOT NULL AND OLD.sub_notes IS NULL)) OR
        (NEW.transaction_description <> OLD.transaction_description OR (NEW.transaction_description IS NULL AND OLD.transaction_description IS NOT NULL) OR (NEW.transaction_description IS NOT NULL AND OLD.transaction_description IS NULL)) OR
        (NEW.country_withdraw <> OLD.country_withdraw OR (NEW.country_withdraw IS NULL AND OLD.country_withdraw IS NOT NULL) OR (NEW.country_withdraw IS NOT NULL AND OLD.country_withdraw IS NULL)) OR
        (NEW.country_used <> OLD.country_used OR (NEW.country_used IS NULL AND OLD.country_used IS NOT NULL) OR (NEW.country_used IS NOT NULL AND OLD.country_used IS NULL)) OR
        (NEW.account_name <> OLD.account_name OR (NEW.account_name IS NULL AND OLD.account_name IS NOT NULL) OR (NEW.account_name IS NOT NULL AND OLD.account_name IS NULL)) OR
        (NEW.currency <> OLD.currency OR (NEW.currency IS NULL AND OLD.currency IS NOT NULL) OR (NEW.currency IS NOT NULL AND OLD.currency IS NULL)) OR
        (NEW.payeer <> OLD.payeer OR (NEW.payeer IS NULL AND OLD.payeer IS NOT NULL) OR (NEW.payeer IS NOT NULL AND OLD.payeer IS NULL)) OR
        (NEW.paid_to <> OLD.paid_to OR (NEW.paid_to IS NULL AND OLD.paid_to IS NOT NULL) OR (NEW.paid_to IS NOT NULL AND OLD.paid_to IS NULL)) OR
        (NEW.amount <> OLD.amount OR (NEW.amount IS NULL AND OLD.amount IS NOT NULL) OR (NEW.amount IS NOT NULL AND OLD.amount IS NULL))
    ) THEN
        SET NEW.checkbox = 0;
    END IF;
END //

DELIMITER ;

DELIMITER //

DROP PROCEDURE IF EXISTS finalize_transactions_status//


CREATE PROCEDURE finalize_transactions_status()
BEGIN
    DECLARE done INT DEFAULT 0;
    DECLARE trans_id INT;
    DECLARE trans_date DATE;
    DECLARE trans_segment VARCHAR(255);
    DECLARE trans_type VARCHAR(255);
    DECLARE trans_sub_type VARCHAR(255);
    DECLARE trans_category VARCHAR(255);
    DECLARE trans_country_used VARCHAR(255);
    DECLARE trans_account_name VARCHAR(255);
    DECLARE trans_currency VARCHAR(255);
    DECLARE trans_payeer VARCHAR(255);
    DECLARE trans_paid_to VARCHAR(255);
    DECLARE trans_amount DECIMAL(10,2);

    DECLARE trans_cursor CURSOR FOR 
        SELECT transaction_id, date, segment, type, sub_type, category, country_used, account_name, currency, payeer, paid_to, amount
        FROM Transactions_Temp;

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = 1;

    OPEN trans_cursor;

    read_loop: LOOP
        FETCH trans_cursor INTO trans_id, trans_date, trans_segment, trans_type, trans_sub_type, trans_category, trans_country_used, trans_account_name, trans_currency, trans_payeer, trans_paid_to, trans_amount;
        IF done THEN
            LEAVE read_loop;
        END IF;

        IF trans_date IS NULL OR trans_segment IS NULL OR trans_type IS NULL OR trans_sub_type IS NULL OR
           trans_category IS NULL OR trans_country_used IS NULL OR trans_account_name IS NULL OR
           trans_currency IS NULL OR trans_payeer IS NULL OR trans_paid_to IS NULL OR trans_amount IS NULL THEN
            UPDATE Transactions_Temp SET status = 'not ready' WHERE transaction_id = trans_id;
        ELSE
            UPDATE Transactions_Temp SET status = 'ready' WHERE transaction_id = trans_id;
        END IF;
    END LOOP;

    CLOSE trans_cursor;
END //

DELIMITER ;


-- Create a log table to track changes
CREATE TABLE IF NOT EXISTS Transaction_Logs (
    log_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    transaction_id INT NOT NULL,
    change_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create a trigger that logs any changes (insert or update) to Transactions_Temp_{username}
DELIMITER $$

CREATE TRIGGER log_transaction_changes
AFTER UPDATE ON Transactions_Temp_{username}
FOR EACH ROW
BEGIN
    -- Insert the transaction_id into the log table
    INSERT INTO Transaction_Logs (transaction_id) VALUES (NEW.transaction_id);
END$$

DELIMITER ;
