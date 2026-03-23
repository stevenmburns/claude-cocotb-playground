// Top-level 24-bit GCD over SPI for Vicharak Shrike (SLG47910V)
//
// Protocol (SPI Mode 0, MSB-first bits, LSB-first bytes, 50 MHz oscillator):
//   Transaction 1 (6 bytes, SS_N held low):
//     a[7:0], a[15:8], a[23:16], b[7:0], b[15:8], b[23:16]
//   GCD starts when SS_N deasserts; poll result_ready; when high:
//   Transaction 2 (3 bytes, SS_N held low):
//     MOSI ignored; MISO returns r[7:0], r[15:8], r[23:16]
//
// Pinout (board names):
//   spi_sck      ← RP_IO10 → FPGA_IO0  (jumper wire)
//   spi_mosi     ← RP_IO11 → FPGA_IO1  (jumper wire)
//   spi_miso     → RP_IO8  ← FPGA_IO2  (jumper wire)
//   spi_ss_n     ← RP_IO9  → FPGA_IO7  (jumper wire)
//   ext_rst      ← RP_IO0  → internal   (PCB trace)
//   result_ready → RP_IO1  ← internal   (PCB trace)
(* top *)
module spi_gcd_top (
    (* iopad_external_pin, clkbuf_inhibit *) input  wire clk,             // 50 MHz on-chip oscillator
    (* iopad_external_pin *)                 output wire clk_en,           // clock enable (always 1)
    (* iopad_external_pin *)                 input  wire ext_rst,          // external reset from RP2040
    (* iopad_external_pin *)                 input  wire spi_ss_n,         // SPI target select (active low)
    (* iopad_external_pin *)                 input  wire spi_sck,          // SPI clock
    (* iopad_external_pin *)                 input  wire spi_mosi,         // SPI MOSI
    (* iopad_external_pin *)                 output wire spi_miso,         // SPI MISO
    (* iopad_external_pin *)                 output wire spi_miso_oe,      // MISO output enable (always 1)
    (* iopad_external_pin *)                 output wire result_ready,     // high when GCD result is ready to read
    (* iopad_external_pin *)                 output wire result_ready_oe   // OE for result_ready (always 1)
);

    assign clk_en         = 1'b1;
    assign spi_miso_oe    = 1'b1;
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
    // SPI target instance
    // -----------------------------------------------------------------------
    wire [7:0] rx_data;
    wire       rx_data_valid;
    reg        rx_data_valid_prev;
    wire       rx_data_valid_pulse;   // single-cycle rising-edge strobe
    reg  [7:0] tx_data_reg;

    always @(posedge clk) rx_data_valid_prev <= rx_data_valid;
    assign rx_data_valid_pulse = rx_data_valid & ~rx_data_valid_prev;

    spi_target #(
        .CPOL  (1'b0),
        .CPHA  (1'b0),
        .WIDTH (8),
        .LSB   (1'b0)
    ) u_spi (
        .i_clk          (clk),
        .i_rst_n        (~rst),
        .i_enable        (1'b1),
        .i_ss_n         (spi_ss_n),
        .i_sck          (spi_sck),
        .i_mosi         (spi_mosi),
        .o_miso         (spi_miso),
        .o_miso_oe      (),           // tied separately at top level
        .o_rx_data      (rx_data),
        .o_rx_data_valid(rx_data_valid),
        .i_tx_data      (tx_data_reg),
        .o_tx_data_hold ()
    );

    // -----------------------------------------------------------------------
    // GCD core (24-bit)
    // -----------------------------------------------------------------------
    reg  [23:0] gcd_a = 0, gcd_b = 0;
    reg         gcd_start = 0;
    wire [23:0] gcd_result;
    wire        gcd_done;

    gcd #(.WIDTH(24)) u_gcd (
        .clk   (clk),
        .rst   (rst),
        .start (gcd_start),
        .a     (gcd_a),
        .b     (gcd_b),
        .result(gcd_result),
        .done  (gcd_done)
    );

    // -----------------------------------------------------------------------
    // Control FSM — 6-byte RX (a then b, LSB-first bytes), 3-byte TX result
    // -----------------------------------------------------------------------
    localparam WAIT_A0      = 4'd0;   // receive a[7:0]
    localparam WAIT_A1      = 4'd1;   // receive a[15:8]
    localparam WAIT_A2      = 4'd2;   // receive a[23:16]
    localparam WAIT_B0      = 4'd3;   // receive b[7:0]
    localparam WAIT_B1      = 4'd4;   // receive b[15:8]
    localparam WAIT_B2      = 4'd5;   // receive b[23:16]
    localparam WAIT_SS      = 4'd6;   // wait for SS_N to deassert
    localparam START_GCD    = 4'd7;
    localparam COMPUTING    = 4'd8;
    localparam WAIT_RESULT0 = 4'd9;   // result_ready; tx_data_reg = r[7:0]
    localparam WAIT_RESULT1 = 4'd10;  // tx_data_reg = r[15:8]
    localparam WAIT_RESULT2 = 4'd11;  // tx_data_reg = r[23:16]

    reg [3:0]  state = 0;
    reg [23:0] result_reg = 0;

    assign result_ready = (state == WAIT_RESULT0);

    // Synced SS_N for clean level detection in the FSM
    reg [1:0] ss_n_sync;
    always @(posedge clk) ss_n_sync <= {ss_n_sync[0], spi_ss_n};

    always @(posedge clk) begin
        gcd_start <= 1'b0;

        if (rst) begin
            state       <= WAIT_A0;
            gcd_a       <= 24'd0;
            gcd_b       <= 24'd0;
            result_reg  <= 24'd0;
            tx_data_reg <= 8'd0;
        end else begin
            case (state)
                WAIT_A0: if (rx_data_valid_pulse) begin
                    gcd_a[7:0] <= rx_data;
                    state      <= WAIT_A1;
                end

                WAIT_A1: if (rx_data_valid_pulse) begin
                    gcd_a[15:8] <= rx_data;
                    state       <= WAIT_A2;
                end

                WAIT_A2: if (rx_data_valid_pulse) begin
                    gcd_a[23:16] <= rx_data;
                    state        <= WAIT_B0;
                end

                WAIT_B0: if (rx_data_valid_pulse) begin
                    gcd_b[7:0] <= rx_data;
                    state      <= WAIT_B1;
                end

                WAIT_B1: if (rx_data_valid_pulse) begin
                    gcd_b[15:8] <= rx_data;
                    state       <= WAIT_B2;
                end

                WAIT_B2: if (rx_data_valid_pulse) begin
                    gcd_b[23:16] <= rx_data;
                    state        <= WAIT_SS;
                end

                // Wait for SS_N to deassert — input transaction is fully done
                WAIT_SS: begin
                    if (ss_n_sync[1]) begin
                        state <= START_GCD;
                    end
                end

                START_GCD: begin
                    gcd_start <= 1'b1;
                    state     <= COMPUTING;
                end

                COMPUTING: if (gcd_done) begin
                    result_reg  <= gcd_result;
                    tx_data_reg <= gcd_result[7:0];
                    state       <= WAIT_RESULT0;
                end

                // result_ready high here; host reads byte 0
                WAIT_RESULT0: if (rx_data_valid_pulse) begin
                    tx_data_reg <= result_reg[15:8];
                    state       <= WAIT_RESULT1;
                end

                // host reads byte 1
                WAIT_RESULT1: if (rx_data_valid_pulse) begin
                    tx_data_reg <= result_reg[23:16];
                    state       <= WAIT_RESULT2;
                end

                // host reads byte 2; back to start
                WAIT_RESULT2: if (rx_data_valid_pulse) begin
                    state <= WAIT_A0;
                end

                default: state <= WAIT_A0;
            endcase
        end
    end

endmodule
