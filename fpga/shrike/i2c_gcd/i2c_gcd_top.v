// Top-level 8-bit GCD over I2C for Vicharak Shrike (SLG47910V)
//
// Protocol (I2C target address 0x08, 50 MHz on-chip oscillator):
//   Transaction 1: Master writes byte a   -> o_int_rx fires; FSM latches reg_a
//   Transaction 2: Master writes byte b   -> o_int_rx fires; FSM starts GCD
//   Poll result_ready; when high:
//   Transaction 3: Master reads 1 byte    -> o_int_tx fires; FSM returns to WAIT_A
//
// External reset via RP2040 GPIO2 → FPGA GPIO3 (PIN 16) PCB trace.
(* top *)
module i2c_gcd_top (
    (* iopad_external_pin, clkbuf_inhibit *) input  wire clk,          // 50 MHz on-chip oscillator
    (* iopad_external_pin *)                 output wire clk_en,        // clock enable (always 1)
    (* iopad_external_pin *)                 input  wire ext_rst,       // external reset from RP2040
    (* iopad_external_pin *)                 input  wire i2c_scl,       // I2C clock (input only)
    (* iopad_external_pin *)                 input  wire i2c_sda_in,    // I2C SDA input
    (* iopad_external_pin *)                 output wire i2c_sda_out,   // I2C SDA output (always 0; driven via OE)
    (* iopad_external_pin *)                 output wire i2c_sda_oe,    // I2C SDA output enable (active high = pull low)
    (* iopad_external_pin *)                 output wire result_ready,  // high when GCD result is ready to read
    (* iopad_external_pin *)                 output wire result_ready_oe // OE for result_ready (always 1)
);

    assign clk_en         = 1'b1;
    assign result_ready_oe = 1'b1;

    // -----------------------------------------------------------------------
    // External reset synchroniser
    // -----------------------------------------------------------------------
    reg rst_sync0 = 0, rst_sync1 = 0;
    always @(posedge clk) begin
        rst_sync0 <= ext_rst;
        rst_sync1 <= rst_sync0;
    end
    wire rst = rst_sync1;

    // -----------------------------------------------------------------------
    // I2C target instance
    // -----------------------------------------------------------------------
    wire [7:0] rx_data;
    wire       int_rx;   // 1-cycle pulse: master wrote a byte
    wire       int_tx;   // 1-cycle pulse: master read a byte (target sent it)
    reg  [7:0] tx_data_reg = 0;

    i2c_target #(
        .I2C_TARGET_ADR(7'h08)
    ) u_i2c (
        .i_clk      (clk),
        .i_rst      (rst),
        .i_en       (1'b1),
        .o_busy     (),
        .i_scl      (i2c_scl),
        .i_sda      (i2c_sda_in),
        .o_sda      (i2c_sda_out),
        .o_sda_oe   (i2c_sda_oe),
        .i_data_tx  (tx_data_reg),
        .o_data_rx  (rx_data),
        .o_int_tx   (int_tx),
        .o_int_rx   (int_rx)
    );

    // -----------------------------------------------------------------------
    // GCD core (8-bit for fast P&R)
    // -----------------------------------------------------------------------
    reg  [7:0] gcd_a = 0, gcd_b = 0;
    reg        gcd_start = 0;
    wire [7:0] gcd_result;
    wire       gcd_done;

    gcd #(.WIDTH(8)) u_gcd (
        .clk   (clk),
        .rst   (rst),
        .start (gcd_start),
        .a     (gcd_a),
        .b     (gcd_b),
        .result(gcd_result),
        .done  (gcd_done)
    );

    // -----------------------------------------------------------------------
    // Control FSM (5 states — no WAIT_SS needed; int_rx/int_tx are clean pulses)
    // -----------------------------------------------------------------------
    localparam WAIT_A      = 3'd0;
    localparam WAIT_B      = 3'd1;
    localparam START_GCD   = 3'd2;
    localparam COMPUTING   = 3'd3;
    localparam WAIT_RESULT = 3'd4;

    reg [2:0] state = 0;
    reg [7:0] reg_a = 0;

    assign result_ready = (state == WAIT_RESULT);

    always @(posedge clk) begin
        // Default: pulses are 1 cycle wide
        gcd_start <= 1'b0;

        if (rst) begin
            state       <= WAIT_A;
            reg_a       <= 8'd0;
            gcd_a       <= 8'd0;
            gcd_b       <= 8'd0;
            tx_data_reg <= 8'd0;
        end else begin
            case (state)
                // Wait for first byte (operand a)
                WAIT_A: begin
                    if (int_rx) begin
                        reg_a <= rx_data;
                        state <= WAIT_B;
                    end
                end

                // Wait for second byte (operand b); kick off GCD
                WAIT_B: begin
                    if (int_rx) begin
                        gcd_a <= reg_a;
                        gcd_b <= rx_data;
                        state <= START_GCD;
                    end
                end

                // Assert gcd_start for one clock cycle
                START_GCD: begin
                    gcd_start <= 1'b1;
                    state     <= COMPUTING;
                end

                // Wait for GCD core; latch result into I2C TX buffer
                COMPUTING: begin
                    if (gcd_done) begin
                        tx_data_reg <= gcd_result;
                        state       <= WAIT_RESULT;
                    end
                end

                // result_ready is high; wait for master to read the result
                WAIT_RESULT: begin
                    if (int_tx) begin
                        state <= WAIT_A;
                    end
                end

                default: state <= WAIT_A;
            endcase
        end
    end

endmodule
